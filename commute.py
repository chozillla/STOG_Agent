#!/usr/bin/env python3
"""
S-Tog Commute Helper: Kildedal → Fuglsang Allé
Uses the Rejseplanen public REST API 2.0 (www.rejseplanen.dk/api).
"""

import json
import os
import sys
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError
from urllib.parse import urlencode

from dotenv import load_dotenv

load_dotenv()

REJSEPLANEN_API_KEY = os.environ.get("REJSEPLANEN_API_KEY", "")
if not REJSEPLANEN_API_KEY:
    print("\033[91mError: REJSEPLANEN_API_KEY not set in .env file\033[0m")
    sys.exit(1)

BASE_URL = "https://www.rejseplanen.dk/api"
WALK_MINUTES = 7
MAX_STATION_WAIT = 2  # max minutes willing to wait at the station

# ANSI color codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


class RejseplanenREST:
    """Client for the Rejseplanen REST API 2.0."""

    def __init__(self):
        self.base_url = BASE_URL
        self.access_id = REJSEPLANEN_API_KEY

    def _get(self, endpoint, params):
        params["accessId"] = self.access_id
        params["format"] = "json"
        url = f"{self.base_url}/{endpoint}?{urlencode(params)}"
        request = Request(url, headers={"User-Agent": "sTOG-commute/1.0"})
        try:
            with urlopen(request, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except URLError as e:
            print(f"{RED}Network error: {e}{RESET}")
            sys.exit(1)

    def location_search(self, query):
        """Search for stations/stops by name."""
        result = self._get("location.name", {"input": query})
        entries = result.get("stopLocationOrCoordLocation", [])
        stops = []
        for entry in entries:
            sl = entry.get("StopLocation")
            if sl:
                stops.append(sl)
        return stops

    def search_trips(self, origin_id, dest_id, num_results=6):
        """Search for trips between two stations."""
        result = self._get("trip", {
            "originId": origin_id,
            "destId": dest_id,
            "numF": num_results,
            "useBus": "0",
            "useMetro": "0",
        })
        trips = result.get("Trip", [])
        if isinstance(trips, dict):
            trips = [trips]
        return trips

    def get_departures(self, station_id, direction_id=None):
        """Get departure board for a station."""
        params = {"id": station_id}
        if direction_id:
            params["direction"] = direction_id
        result = self._get("departureBoard", params)
        departures = result.get("Departure", [])
        if isinstance(departures, dict):
            departures = [departures]
        return departures


def parse_time(date_str, time_str):
    """Parse REST API date (YYYY-MM-DD) and time (HH:MM:SS) into datetime."""
    return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")


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
        fuglsang = api.location_search("Fuglsang Alle")
        if not fuglsang:
            fuglsang = api.location_search("Fuglsang")
            if not fuglsang:
                print(f"{RED}Could not find Fuglsang Allé{RESET}")
                return

    origin = kildedal[0]
    dest = fuglsang[0]
    origin_id = origin.get("extId", "")
    dest_id = dest.get("extId", "")

    print(f"  From: {origin.get('name', 'Unknown')}")
    print(f"  To:   {dest.get('name', 'Unknown')}\n")

    # Step 2: Search trips
    print(f"{DIM}Searching trips...{RESET}\n")
    trips = api.search_trips(origin_id, dest_id)

    if not trips:
        print(f"{YELLOW}No trips found{RESET}")
        return

    now = datetime.now()
    total_lead = WALK_MINUTES + MAX_STATION_WAIT

    print(f"{BOLD}{'#':<3} {'Leave office':<14} {'At station':<12} {'Depart':<10} {'Arrive':<10} {'Wait':<6} {'Dur':<8} {'Chg':<5} {'Status'}{RESET}")
    print("─" * 95)

    for i, trip in enumerate(trips, 1):
        legs = trip.get("LegList", {}).get("Leg", [])
        if isinstance(legs, dict):
            legs = [legs]
        if not legs:
            continue

        first_leg = legs[0]
        last_leg = legs[-1]

        # Departure from origin
        dep_origin = first_leg.get("Origin", {})
        dep_date = dep_origin.get("date", "")
        dep_time_str = dep_origin.get("time", "")
        dep_rt_date = dep_origin.get("rtDate", "")
        dep_rt_time = dep_origin.get("rtTime", "")

        # Arrival at destination
        arr_dest = last_leg.get("Destination", {})
        arr_date = arr_dest.get("date", "")
        arr_time_str = arr_dest.get("time", "")
        arr_rt_date = arr_dest.get("rtDate", "")
        arr_rt_time = arr_dest.get("rtTime", "")

        if not dep_time_str or not arr_time_str:
            continue

        dep_scheduled = parse_time(dep_date, dep_time_str)
        arr_scheduled = parse_time(arr_date, arr_time_str)

        dep_realtime = parse_time(dep_rt_date, dep_rt_time) if dep_rt_time else None
        arr_realtime = parse_time(arr_rt_date, arr_rt_time) if arr_rt_time else None

        dep_effective = dep_realtime if dep_realtime else dep_scheduled
        arr_effective = arr_realtime if arr_realtime else arr_scheduled

        # Leave office timing
        leave_by = dep_effective - timedelta(minutes=total_lead)
        at_station = leave_by + timedelta(minutes=WALK_MINUTES)
        station_wait = int((dep_effective - at_station).total_seconds() / 60)

        # Duration
        duration = arr_effective - dep_effective
        dur_min = int(duration.total_seconds() / 60)
        dur_str = f"{dur_min // 60}h{dur_min % 60:02d}m" if dur_min >= 60 else f"{dur_min}m"

        # Changes (number of transport legs minus 1)
        transport_legs = [l for l in legs if l.get("type") != "WALK"]
        changes = max(0, len(transport_legs) - 1)

        # Status / delay
        dep_delay = format_delay(dep_scheduled, dep_realtime)

        cancelled = first_leg.get("cancelled", False)
        status = f"{RED}CANCELLED{RESET}" if cancelled else dep_delay

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
        leg_parts = []
        for leg in legs:
            leg_type = leg.get("type", "")
            if leg_type == "WALK":
                leg_parts.append("Walk")
            else:
                name = leg.get("name", "").strip()
                if name:
                    leg_parts.append(name)
        if leg_parts:
            print(f"    {DIM}→ {' → '.join(leg_parts)}{RESET}")

    print()
    print(f"{DIM}Updated: {now.strftime('%H:%M:%S')} | Walk: {WALK_MINUTES} min | Max station wait: {MAX_STATION_WAIT} min | Leave {total_lead} min before departure{RESET}")


def main():
    api = RejseplanenREST()

    if len(sys.argv) > 1 and sys.argv[1] == "search":
        query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Kildedal"
        results = api.location_search(query)
        print(f"\nSearch results for '{query}':")
        for loc in results:
            print(f"  {loc.get('name', '?'):<40} extId: {loc.get('extId', '?')}")
            lon, lat = loc.get("lon", ""), loc.get("lat", "")
            if lon and lat:
                print(f"  {'':40} coords: {lon}, {lat}")
        return

    if len(sys.argv) > 1 and sys.argv[1] == "departures":
        print(f"\n{DIM}Looking up Kildedal...{RESET}")
        results = api.location_search("Kildedal St.")
        if results:
            station = results[0]
            print(f"\n{BOLD}Departures from {station.get('name', '?')}{RESET}\n")
            departures = api.get_departures(station.get("extId", ""))
            for dep in departures:
                date = dep.get("date", "")
                time_str = dep.get("time", "")
                rt_date = dep.get("rtDate", "")
                rt_time = dep.get("rtTime", "")
                name = dep.get("name", "").strip()
                direction = dep.get("direction", "")

                scheduled = parse_time(date, time_str) if time_str else None
                realtime = parse_time(rt_date, rt_time) if rt_time else None
                delay = format_delay(scheduled, realtime) if scheduled else ""

                time_display = scheduled.strftime("%H:%M") if scheduled else "??:??"
                if realtime and realtime != scheduled:
                    time_display += f" → {realtime.strftime('%H:%M')}"

                print(f"  {time_display:<16} {name:<15} {direction:<30} {delay}")
        return

    # Default: show trip options
    display_trips(api)


if __name__ == "__main__":
    main()
