#!/usr/bin/env python3
"""
S-Tog Commute Helper: Kildedal → Fuglsang Allé
Uses the Rejseplanen public REST API 2.0 (www.rejseplanen.dk/api).
"""

import json
import os
import sys
import webbrowser
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

    def search_trips(self, origin_id=None, dest_id=None, num_results=6,
                     poly=False, origin_coord=None, dest_coord=None):
        """Search for trips between two stations (by ID or coordinates)."""
        params = {"numF": num_results}
        if origin_coord and dest_coord:
            params["originCoordLat"] = origin_coord[0]
            params["originCoordLong"] = origin_coord[1]
            params["destCoordLat"] = dest_coord[0]
            params["destCoordLong"] = dest_coord[1]
        else:
            params["originId"] = origin_id
            params["destId"] = dest_id
            params["useBus"] = "0"
            params["useMetro"] = "0"
        if poly:
            params["poly"] = "1"
        result = self._get("trip", params)
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


def extract_polylines(trip):
    """Extract polyline coordinates from a trip's legs."""
    legs = trip.get("LegList", {}).get("Leg", [])
    if isinstance(legs, dict):
        legs = [legs]
    polylines = []
    for leg in legs:
        leg_type = leg.get("type", "")
        name = leg.get("name", "").strip() if leg_type != "WALK" else "Walk"
        # Get coordinate array from the appropriate polyline location
        crd = None
        if leg_type == "WALK":
            pg = leg.get("GisRoute", {}).get("polylineGroup", {})
        else:
            pg = leg.get("PolylineGroup", {})
        descs = pg.get("polylineDesc", [])
        if isinstance(descs, dict):
            descs = [descs]
        for desc in descs:
            c = desc.get("crd", [])
            if c:
                crd = c
                break
        if not crd or len(crd) < 2:
            continue
        # Convert flat [lon, lat, lon, lat, ...] to [[lat, lon], ...]
        coords = [[crd[i + 1], crd[i]] for i in range(0, len(crd) - 1, 2)]
        polylines.append({"name": name, "type": leg_type, "coordinates": coords})
    return polylines


def process_trips(raw_trips):
    """Process raw trip data into the format needed by the map UI."""
    TRANSPORT_COLORS = [
        "#0074d9", "#e6550d", "#2ca02c", "#d62728",
        "#9467bd", "#8c564b", "#e377c2", "#17becf",
    ]
    trips_data = []
    for trip in raw_trips:
        polylines = extract_polylines(trip)
        if not polylines:
            continue

        legs_raw = trip.get("LegList", {}).get("Leg", [])
        if isinstance(legs_raw, dict):
            legs_raw = [legs_raw]

        first_leg = legs_raw[0]
        last_leg = legs_raw[-1]
        dep_origin = first_leg.get("Origin", {})
        arr_dest = last_leg.get("Destination", {})

        dep_time = dep_origin.get("rtTime", dep_origin.get("time", ""))
        arr_time = arr_dest.get("rtTime", arr_dest.get("time", ""))
        dep_date = dep_origin.get("rtDate", dep_origin.get("date", ""))
        arr_date = arr_dest.get("rtDate", arr_dest.get("date", ""))

        departure_str = dep_time[:5] if dep_time else "??:??"
        arrival_str = arr_time[:5] if arr_time else "??:??"

        dur_min = 0
        if dep_time and arr_time and dep_date and arr_date:
            dep_dt = parse_time(dep_date, dep_time)
            arr_dt = parse_time(arr_date, arr_time)
            dur_min = int((arr_dt - dep_dt).total_seconds() / 60)
        duration_str = f"{dur_min // 60}h{dur_min % 60:02d}m" if dur_min >= 60 else f"{dur_min}m"

        transport_legs = [l for l in legs_raw if l.get("type") != "WALK"]
        transfers = max(0, len(transport_legs) - 1)

        legs_info = []
        color_idx = 0
        for pl in polylines:
            if pl["type"] == "WALK":
                color = "#888"
            else:
                color = TRANSPORT_COLORS[color_idx % len(TRANSPORT_COLORS)]
                color_idx += 1
            legs_info.append({
                "name": pl["name"],
                "type": pl["type"],
                "color": color,
                "coordinates": pl["coordinates"],
            })

        trips_data.append({
            "index": len(trips_data),
            "departure": departure_str,
            "arrival": arrival_str,
            "duration": duration_str,
            "transfers": transfers,
            "legs": legs_info,
        })
    return trips_data


def generate_map(api):
    """Start a local HTTP server with an interactive drop-pin route map."""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from urllib.parse import urlparse, parse_qs

    MAP_HTML = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<title>S-Tog Route Map</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { display: flex; height: 100vh; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
#sidebar {
  width: 340px; min-width: 340px; height: 100vh; overflow-y: auto;
  background: #f8f9fa; border-right: 1px solid #dee2e6; padding: 16px;
}
#sidebar h2 { font-size: 16px; margin-bottom: 12px; color: #333; }
#map { flex: 1; height: 100vh; }
.trip-card {
  background: white; border: 2px solid #dee2e6; border-radius: 8px;
  padding: 12px; margin-bottom: 10px; cursor: pointer; transition: all 0.15s;
}
.trip-card:hover { border-color: #adb5bd; background: #fff; }
.trip-card.selected { border-color: #0074d9; background: #e8f4fd; }
.trip-times { font-size: 18px; font-weight: 600; color: #212529; }
.trip-meta { font-size: 13px; color: #6c757d; margin-top: 4px; }
.trip-legs { font-size: 12px; color: #495057; margin-top: 6px; display: flex; flex-wrap: wrap; align-items: center; gap: 4px; }
.leg-badge {
  display: inline-flex; align-items: center; padding: 2px 7px;
  border-radius: 4px; font-size: 11px; font-weight: 500; color: white;
}
.leg-arrow { color: #adb5bd; font-size: 11px; }
#instructions { color: #6c757d; font-size: 14px; line-height: 1.6; }
#instructions .step { margin-bottom: 8px; }
#instructions .num { display: inline-block; width: 22px; height: 22px; line-height: 22px;
  text-align: center; border-radius: 50%; color: white; font-size: 12px; font-weight: 600;
  margin-right: 6px; vertical-align: middle; }
#instructions .num.green { background: #2ca02c; }
#instructions .num.red { background: #d62728; }
.loading { color: #0074d9; font-size: 15px; font-weight: 500; padding: 20px 0; }
</style>
</head>
<body>
<div id="sidebar">
  <h2 id="header">Drop pins to plan a route</h2>
  <div id="trip-list">
    <div id="instructions">
      <div class="step"><span class="num green">1</span> Click the map to set <b>origin</b></div>
      <div class="step"><span class="num red">2</span> Click again to set <b>destination</b></div>
      <div class="step" style="margin-top:12px; font-size:13px; color:#adb5bd;">Drag pins to adjust. Click map with both pins to reset.</div>
    </div>
  </div>
</div>
<div id="map"></div>
<script>
var map = L.map('map').setView([55.68, 12.5], 12);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OSM', maxZoom: 18
}).addTo(map);

// Try geolocation
if (navigator.geolocation) {
  navigator.geolocation.getCurrentPosition(function(pos) {
    map.setView([pos.coords.latitude, pos.coords.longitude], 13);
  });
}

var originMarker = null, destMarker = null;
var tripLayers = [];
var trips = [];
var selectedIndex = 0;
var fetching = false;

function clearRoutes() {
  tripLayers.forEach(function(layers) {
    layers.forEach(function(pl) { map.removeLayer(pl); });
  });
  tripLayers = [];
  trips = [];
}

function fetchRoutes() {
  if (!originMarker || !destMarker) return;
  fetching = true;
  clearRoutes();
  var listEl = document.getElementById('trip-list');
  listEl.innerHTML = '<div class="loading">Searching routes...</div>';
  document.getElementById('header').textContent = 'Searching...';

  var o = originMarker.getLatLng(), d = destMarker.getLatLng();
  fetch('/api/trips?olat=' + o.lat + '&olon=' + o.lng + '&dlat=' + d.lat + '&dlon=' + d.lng)
    .then(function(r) { return r.json(); })
    .then(function(data) {
      fetching = false;
      trips = data;
      if (!trips.length) {
        listEl.innerHTML = '<div style="color:#6c757d;padding:10px;">No routes found. Try different locations.</div>';
        document.getElementById('header').textContent = 'No routes found';
        return;
      }
      document.getElementById('header').textContent = trips.length + ' route' + (trips.length > 1 ? 's' : '') + ' found';
      renderTrips();
    })
    .catch(function(err) {
      fetching = false;
      listEl.innerHTML = '<div style="color:#d62728;padding:10px;">Error fetching routes: ' + err.message + '</div>';
      document.getElementById('header').textContent = 'Error';
    });
}

function renderTrips() {
  // Draw polylines
  trips.forEach(function(trip) {
    var layers = [];
    trip.legs.forEach(function(leg) {
      var opts = { color: '#aaa', weight: 3, opacity: 0.35, interactive: true };
      if (leg.type === 'WALK') opts.dashArray = '6, 8';
      var pl = L.polyline(leg.coordinates, opts).addTo(map);
      pl._tripIndex = trip.index;
      pl._legColor = leg.color;
      pl._legType = leg.type;
      pl.on('click', function() { selectTrip(trip.index); });
      layers.push(pl);
    });
    tripLayers.push(layers);
  });

  // Build sidebar cards
  var listEl = document.getElementById('trip-list');
  listEl.innerHTML = '';
  trips.forEach(function(trip) {
    var card = document.createElement('div');
    card.className = 'trip-card';
    card.id = 'trip-card-' + trip.index;
    card.onclick = function() { selectTrip(trip.index); };

    var legHtml = '';
    trip.legs.forEach(function(leg, i) {
      if (i > 0) legHtml += '<span class="leg-arrow">&rarr;</span>';
      var bg = leg.color;
      if (leg.type === 'WALK') bg = '#6c757d';
      legHtml += '<span class="leg-badge" style="background:' + bg + '">' + leg.name + '</span>';
    });

    var transferText = trip.transfers === 0 ? 'Direct' : trip.transfers + ' transfer' + (trip.transfers > 1 ? 's' : '');

    card.innerHTML =
      '<div class="trip-times">' + trip.departure + ' &rarr; ' + trip.arrival + '</div>' +
      '<div class="trip-meta">' + trip.duration + ' &middot; ' + transferText + '</div>' +
      '<div class="trip-legs">' + legHtml + '</div>';
    listEl.appendChild(card);
  });

  selectTrip(0);
}

function selectTrip(index) {
  selectedIndex = index;
  tripLayers.forEach(function(layers) {
    layers.forEach(function(pl) {
      pl.setStyle({ color: '#aaa', weight: 3, opacity: 0.35 });
      pl.bringToBack();
    });
  });
  var bounds = L.latLngBounds([]);
  tripLayers[index].forEach(function(pl) {
    var dash = pl._legType === 'WALK' ? '6, 8' : null;
    pl.setStyle({ color: pl._legColor, weight: 6, opacity: 0.9, dashArray: dash });
    pl.bringToFront();
    bounds.extend(pl.getBounds());
  });
  // Include markers in bounds
  if (originMarker) bounds.extend(originMarker.getLatLng());
  if (destMarker) bounds.extend(destMarker.getLatLng());
  map.fitBounds(bounds, { padding: [50, 50] });

  document.querySelectorAll('.trip-card').forEach(function(c) {
    c.classList.remove('selected');
  });
  var card = document.getElementById('trip-card-' + index);
  if (card) {
    card.classList.add('selected');
    card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}

var greenIcon = L.icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41]
});
var redIcon = L.icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41]
});

map.on('click', function(e) {
  if (fetching) return;
  if (!originMarker) {
    originMarker = L.marker(e.latlng, { icon: greenIcon, draggable: true }).addTo(map)
      .bindPopup('Origin').openPopup();
    originMarker.on('dragend', function() { if (destMarker) fetchRoutes(); });
  } else if (!destMarker) {
    destMarker = L.marker(e.latlng, { icon: redIcon, draggable: true }).addTo(map)
      .bindPopup('Destination').openPopup();
    destMarker.on('dragend', function() { fetchRoutes(); });
    fetchRoutes();
  } else {
    // Both pins exist: reset
    map.removeLayer(originMarker);
    map.removeLayer(destMarker);
    originMarker = null;
    destMarker = null;
    clearRoutes();
    document.getElementById('trip-list').innerHTML =
      '<div id="instructions">' +
      '<div class="step"><span class="num green">1</span> Click the map to set <b>origin</b></div>' +
      '<div class="step"><span class="num red">2</span> Click again to set <b>destination</b></div>' +
      '<div class="step" style="margin-top:12px; font-size:13px; color:#adb5bd;">Drag pins to adjust. Click map with both pins to reset.</div>' +
      '</div>';
    document.getElementById('header').textContent = 'Drop pins to plan a route';
    // Place new origin
    originMarker = L.marker(e.latlng, { icon: greenIcon, draggable: true }).addTo(map)
      .bindPopup('Origin').openPopup();
    originMarker.on('dragend', function() { if (destMarker) fetchRoutes(); });
  }
});

setTimeout(function() { map.invalidateSize(); }, 100);
</script>
</body>
</html>"""

    class RequestHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/api/trips":
                self._handle_trips(parsed)
            else:
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(MAP_HTML.encode("utf-8"))

        def _handle_trips(self, parsed):
            qs = parse_qs(parsed.query)
            try:
                olat = float(qs["olat"][0])
                olon = float(qs["olon"][0])
                dlat = float(qs["dlat"][0])
                dlon = float(qs["dlon"][0])
            except (KeyError, ValueError, IndexError):
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":"Missing or invalid coordinates"}')
                return

            try:
                raw_trips = api.search_trips(
                    origin_coord=(olat, olon),
                    dest_coord=(dlat, dlon),
                    poly=True,
                    num_results=6,
                )
                trips_data = process_trips(raw_trips)
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
                return

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(json.dumps(trips_data).encode("utf-8"))

        def log_message(self, format, *args):
            # Suppress default request logging
            pass

    port = 8421
    server = HTTPServer(("localhost", port), RequestHandler)
    url = f"http://localhost:{port}"
    print(f"{GREEN}Map server running at {url}{RESET}")
    print(f"{DIM}Ctrl+C to stop{RESET}")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n{DIM}Server stopped.{RESET}")
        server.server_close()


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

    if len(sys.argv) > 1 and sys.argv[1] == "map":
        generate_map(api)
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
