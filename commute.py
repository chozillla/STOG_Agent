#!/usr/bin/env python3
"""
S-Tog Commute Helper: Kildedal → Fuglsang Allé
Uses the HAFAS mgate.exe endpoint (same as Rejseplanen mobile app).
No API key required.
"""

import json
import sys
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError

ENDPOINT = "https://mobilapps.rejseplanen.dk/bin/iphone.exe"
WALK_MINUTES = 7
MAX_STATION_WAIT = 2  # max minutes willing to wait at the station

# ANSI color codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


class RejseplanenHAFAS:
    """Client for Rejseplanen's HAFAS mgate.exe endpoint."""

    def __init__(self):
        self.endpoint = ENDPOINT
        self.base_request = {
            "auth": {"type": "AID", "aid": "irkmpm9mdznstenr-android"},
            "client": {"type": "AND", "id": "DK"},
            "ver": "1.43",
            "ext": "DK.9",
            "lang": "en",
        }

    def _call(self, method, req_data):
        body = {
            **self.base_request,
            "svcReqL": [{"meth": method, "req": req_data}],
        }
        data = json.dumps(body).encode("utf-8")
        request = Request(
            self.endpoint,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Accept-Charset": "utf-8",
                "User-Agent": "sTOG-commute/1.0",
            },
        )
        try:
            with urlopen(request, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except URLError as e:
            print(f"{RED}Network error: {e}{RESET}")
            sys.exit(1)

    def location_search(self, query):
        """Search for stations/stops by name."""
        result = self._call("LocMatch", {
            "input": {"field": "S", "loc": {"name": query, "type": "S"}}
        })
        svc = result.get("svcResL", [{}])[0]
        if svc.get("err", "OK") != "OK":
            print(f"{RED}Location search error: {svc.get('errTxt', 'Unknown')}{RESET}")
            return []
        matches = svc.get("res", {}).get("match", {}).get("locL", [])
        return matches

    def search_trips(self, origin_id, dest_id, num_results=6):
        """Search for trips between two stations."""
        now = datetime.now()
        result = self._call("TripSearch", {
            "depLocL": [{"lid": origin_id}],
            "arrLocL": [{"lid": dest_id}],
            "outDate": now.strftime("%Y%m%d"),
            "outTime": now.strftime("%H%M%S"),
            "jnyFltrL": [{"type": "PROD", "mode": "INC", "value": "127"}],
            "numF": num_results,
            "getPasslist": False,
            "getPolyline": False,
            "getTariff": False,
            "ushrp": True,
            "getPT": True,
            "outFrwd": True,
        })
        return result

    def get_departures(self, station_id, direction_id=None, duration=120):
        """Get departure board for a station."""
        now = datetime.now()
        req = {
            "stbLoc": {"lid": station_id},
            "type": "DEP",
            "date": now.strftime("%Y%m%d"),
            "time": now.strftime("%H%M%S"),
            "dur": duration,
            "jnyFltrL": [{"type": "PROD", "mode": "INC", "value": "127"}],
        }
        if direction_id:
            req["dirLoc"] = {"lid": direction_id}
        result = self._call("StationBoard", req)
        return result


def parse_time(date_str, time_str):
    """Parse HAFAS date/time strings into datetime."""
    # time can have day offset like "1d012300" for next day
    day_offset = 0
    if "d" in time_str:
        parts = time_str.split("d")
        day_offset = int(parts[0])
        time_str = parts[1]
    time_str = time_str.ljust(6, "0")
    dt = datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")
    return dt + timedelta(days=day_offset)


def format_delay(scheduled, realtime):
    """Format delay with color coding."""
    if realtime is None:
        return f"{DIM}(no RT){RESET}"
    diff = (realtime - scheduled).total_seconds() / 60
    if diff <= 0:
        return f"{GREEN}on time{RESET}"
    elif diff <= 3:
        return f"{YELLOW}+{int(diff)} min{RESET}"
    else:
        return f"{RED}+{int(diff)} min{RESET}"


def display_trips(api):
    """Main display: search trips and show leave-by times."""
    print(f"\n{BOLD}=== Kildedal → Fuglsang Allé ==={RESET}")
    print(f"{DIM}Walk to station: {WALK_MINUTES} min | Max station wait: {MAX_STATION_WAIT} min{RESET}\n")

    # Step 1: Find station IDs
    print(f"{DIM}Looking up stations...{RESET}")
    kildedal = api.location_search("Kildedal St.")
    fuglsang = api.location_search("Fuglsang Allé")

    if not kildedal:
        print(f"{RED}Could not find Kildedal station{RESET}")
        return
    if not fuglsang:
        # Try alternative names
        fuglsang = api.location_search("Fuglsang Alle")
        if not fuglsang:
            fuglsang = api.location_search("Fuglsang")
            if not fuglsang:
                print(f"{RED}Could not find Fuglsang Allé{RESET}")
                return

    origin = kildedal[0]
    dest = fuglsang[0]
    origin_lid = origin.get("lid", "")
    dest_lid = dest.get("lid", "")

    print(f"  From: {origin.get('name', 'Unknown')}")
    print(f"  To:   {dest.get('name', 'Unknown')}\n")

    # Step 2: Search trips
    print(f"{DIM}Searching trips...{RESET}\n")
    trip_result = api.search_trips(origin_lid, dest_lid)

    svc = trip_result.get("svcResL", [{}])[0]
    if svc.get("err", "OK") != "OK":
        print(f"{RED}Trip search error: {svc.get('errTxt', 'Unknown')}{RESET}")
        # Show raw error for debugging
        print(f"{DIM}{json.dumps(svc, indent=2)}{RESET}")
        return

    res = svc.get("res", {})
    common = res.get("common", {})
    loc_list = common.get("locL", [])
    prod_list = common.get("prodL", [])
    connections = res.get("outConL", [])

    if not connections:
        print(f"{YELLOW}No trips found{RESET}")
        return

    now = datetime.now()
    total_lead = WALK_MINUTES + MAX_STATION_WAIT  # leave this many min before departure
    print(f"{BOLD}{'#':<3} {'Leave office':<14} {'At station':<12} {'Depart':<10} {'Arrive':<10} {'Wait':<6} {'Dur':<8} {'Chg':<5} {'Status'}{RESET}")
    print("─" * 95)

    for i, conn in enumerate(connections, 1):
        date = conn.get("date", "")
        dep_info = conn.get("dep", {})
        arr_info = conn.get("arr", {})

        # Scheduled times
        dep_time_str = dep_info.get("dTimeS", "")
        arr_time_str = arr_info.get("aTimeS", "")

        if not dep_time_str or not arr_time_str:
            continue

        dep_scheduled = parse_time(date, dep_time_str)
        arr_scheduled = parse_time(date, arr_time_str)

        # Real-time times
        dep_rt_str = dep_info.get("dTimeR", None)
        arr_rt_str = arr_info.get("aTimeR", None)
        dep_realtime = parse_time(date, dep_rt_str) if dep_rt_str else None
        arr_realtime = parse_time(date, arr_rt_str) if arr_rt_str else None

        # Effective departure (use realtime if available)
        dep_effective = dep_realtime if dep_realtime else dep_scheduled
        arr_effective = arr_realtime if arr_realtime else arr_scheduled

        # Leave office: depart - walk - max wait (arrive at station with ≤2 min to spare)
        leave_by = dep_effective - timedelta(minutes=total_lead)
        # Arrive at station: leave + walk time
        at_station = leave_by + timedelta(minutes=WALK_MINUTES)
        # Actual wait at station
        station_wait = int((dep_effective - at_station).total_seconds() / 60)

        # Duration
        duration = arr_effective - dep_effective
        dur_min = int(duration.total_seconds() / 60)
        dur_str = f"{dur_min // 60}h{dur_min % 60:02d}m" if dur_min >= 60 else f"{dur_min}m"

        # Changes
        changes = conn.get("chg", 0)

        # Status / delay
        dep_delay = format_delay(dep_scheduled, dep_realtime)

        # Cancelled?
        cancelled = dep_info.get("dCncl", False) or arr_info.get("aCncl", False)
        if cancelled:
            status = f"{RED}CANCELLED{RESET}"
        else:
            status = dep_delay

        # Color the leave-by time based on urgency
        mins_until = (leave_by - now).total_seconds() / 60
        if mins_until < 0:
            leave_color = RED
            leave_note = " (past)"
        elif mins_until < 5:
            leave_color = YELLOW
            leave_note = " (!)"
        else:
            leave_color = GREEN
            leave_note = ""

        dep_display = dep_scheduled.strftime("%H:%M")
        if dep_realtime and dep_realtime != dep_scheduled:
            dep_display = f"{dep_scheduled.strftime('%H:%M')}→{dep_realtime.strftime('%H:%M')}"

        arr_display = arr_scheduled.strftime("%H:%M")
        if arr_realtime and arr_realtime != arr_scheduled:
            arr_display = f"{arr_scheduled.strftime('%H:%M')}→{arr_realtime.strftime('%H:%M')}"

        wait_str = f"{station_wait}m"

        print(
            f"{i:<3} "
            f"{leave_color}{BOLD}{leave_by.strftime('%H:%M')}{RESET}{leave_note:<7} "
            f"{at_station.strftime('%H:%M'):<12} "
            f"{dep_display:<10} "
            f"{arr_display:<10} "
            f"{wait_str:<6} "
            f"{dur_str:<8} "
            f"{changes:<5} "
            f"{status}"
        )

        # Show trip legs summary
        sections = conn.get("secL", [])
        leg_parts = []
        for sec in sections:
            sec_type = sec.get("type", "")
            if sec_type == "JNY":
                jny = sec.get("jny", {})
                prod_idx = jny.get("prodX", None)
                if prod_idx is not None and prod_idx < len(prod_list):
                    prod = prod_list[prod_idx]
                    leg_parts.append(prod.get("name", "?").strip())
            elif sec_type == "WALK":
                gis = sec.get("gis", {})
                walk_dur = gis.get("durS", "")
                if walk_dur:
                    mins = int(walk_dur[:2]) * 60 + int(walk_dur[2:4])
                    leg_parts.append(f"Walk {mins}m")
                else:
                    leg_parts.append("Walk")
            elif sec_type == "TRSF":
                leg_parts.append("Transfer")
        if leg_parts:
            print(f"    {DIM}→ {' → '.join(leg_parts)}{RESET}")

    print()
    print(f"{DIM}Updated: {now.strftime('%H:%M:%S')} | Walk: {WALK_MINUTES} min | Max station wait: {MAX_STATION_WAIT} min | Leave {total_lead} min before departure{RESET}")


def main():
    api = RejseplanenHAFAS()

    if len(sys.argv) > 1 and sys.argv[1] == "search":
        # Search mode: find station IDs
        query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Kildedal"
        results = api.location_search(query)
        print(f"\nSearch results for '{query}':")
        for loc in results:
            print(f"  {loc.get('name', '?'):<40} lid: {loc.get('lid', '?')}")
            if loc.get("extId"):
                print(f"  {'':40} extId: {loc['extId']}")
        return

    if len(sys.argv) > 1 and sys.argv[1] == "departures":
        # Departures mode: show departure board
        print(f"\n{DIM}Looking up Kildedal...{RESET}")
        results = api.location_search("Kildedal St.")
        if results:
            station = results[0]
            print(f"\n{BOLD}Departures from {station.get('name', '?')}{RESET}\n")
            dep_result = api.get_departures(station.get("lid", ""))
            svc = dep_result.get("svcResL", [{}])[0]
            if svc.get("err", "OK") == "OK":
                res = svc.get("res", {})
                common = res.get("common", {})
                prod_list = common.get("prodL", [])
                journeys = res.get("jnyL", [])
                for jny in journeys:
                    date = jny.get("date", "")
                    stb_stop = jny.get("stbStop", {})
                    dep_time = stb_stop.get("dTimeS", "")
                    dep_rt = stb_stop.get("dTimeR", "")
                    prod_idx = jny.get("prodX", None)
                    prod_name = ""
                    if prod_idx is not None and prod_idx < len(prod_list):
                        prod_name = prod_list[prod_idx].get("name", "").strip()
                    direction = jny.get("dirTxt", "")

                    scheduled = parse_time(date, dep_time) if dep_time else None
                    realtime = parse_time(date, dep_rt) if dep_rt else None
                    delay = format_delay(scheduled, realtime) if scheduled else ""

                    time_display = scheduled.strftime("%H:%M") if scheduled else "??:??"
                    if realtime and realtime != scheduled:
                        time_display += f" → {realtime.strftime('%H:%M')}"

                    print(f"  {time_display:<16} {prod_name:<15} {direction:<30} {delay}")
            else:
                print(f"{RED}Error: {svc.get('errTxt', 'Unknown')}{RESET}")
        return

    # Default: show trip options
    display_trips(api)


if __name__ == "__main__":
    main()
