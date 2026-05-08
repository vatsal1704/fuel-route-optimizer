import { useMemo, useState, useEffect } from "react";
import axios from "axios";
import {
  MapContainer,
  TileLayer,
  Polyline,
  Marker,
  Popup,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Fuel, MapPin, Loader2, Flag, PlayCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Default Leaflet marker icon fix for bundlers
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const fuelIcon = L.divIcon({
  className: "fuel-marker",
  html: `<div style="background:#f59e0b;border:2px solid #1f2937;border-radius:9999px;width:28px;height:28px;display:flex;align-items:center;justify-content:center;color:#1f2937;font-weight:700;box-shadow:0 2px 6px rgba(0,0,0,.35);">⛽</div>`,
  iconSize: [28, 28],
  iconAnchor: [14, 14],
});

const startIcon = L.divIcon({
  className: "start-marker",
  html: `<div style="background:#10b981;border:2px solid #064e3b;border-radius:9999px;width:32px;height:32px;display:flex;align-items:center;justify-content:center;color:white;font-weight:700;box-shadow:0 2px 6px rgba(0,0,0,.35);">A</div>`,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});

const finishIcon = L.divIcon({
  className: "finish-marker",
  html: `<div style="background:#ef4444;border:2px solid #7f1d1d;border-radius:9999px;width:32px;height:32px;display:flex;align-items:center;justify-content:center;color:white;font-weight:700;box-shadow:0 2px 6px rgba(0,0,0,.35);">B</div>`,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});

function FitBounds({ points }) {
  const map = useMap();
  useEffect(() => {
    if (points && points.length > 1) {
      map.fitBounds(points, { padding: [40, 40] });
    }
  }, [points, map]);
  return null;
}

export default function RoutePlanner() {
  const [start, setStart] = useState("Los Angeles, CA");
  const [finish, setFinish] = useState("Dallas, TX");
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [meta, setMeta] = useState(null);

  useEffect(() => {
    axios
      .get(`${API}/health`)
      .then((r) => setMeta(r.data))
      .catch(() => {});
  }, []);

  const submit = async (e) => {
    e?.preventDefault?.();
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const res = await axios.post(`${API}/route/`, { start, finish });
      setData(res.data);
    } catch (err) {
      setError(err?.response?.data?.error || err.message || "Request failed");
    } finally {
      setLoading(false);
    }
  };

  const polyline = data?.route?.polyline || [];
  const center = useMemo(() => {
    if (polyline.length) return polyline[Math.floor(polyline.length / 2)];
    return [39.5, -98.35];
  }, [polyline]);

  return (
    <div
      data-testid="route-planner-page"
      className="min-h-screen bg-[#0b1220] text-slate-100"
      style={{
        fontFamily: '"IBM Plex Sans", "DM Sans", system-ui, sans-serif',
      }}
    >
      <header className="border-b border-slate-800 px-6 lg:px-12 py-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-amber-400 text-slate-900 flex items-center justify-center font-black">
            ⛽
          </div>
          <div>
            <h1 className="text-lg lg:text-xl font-semibold tracking-tight">
              FuelOptimal · USA Route Planner
            </h1>
            <p className="text-xs text-slate-400">
              Django + DRF · OSRM routing · Greedy cost-optimal refueling
            </p>
          </div>
        </div>
        {meta && (
          <Badge
            variant="secondary"
            data-testid="meta-badge"
            className="bg-slate-800 text-slate-200"
          >
            {meta.stations_loaded} stations loaded
          </Badge>
        )}
      </header>

      <main className="grid grid-cols-1 lg:grid-cols-[420px_1fr] gap-0">
        {/* LEFT PANEL */}
        <section className="px-6 lg:px-8 py-8 border-r border-slate-800 bg-[#0e1729] min-h-[calc(100vh-73px)]">
          <h2 className="text-sm font-medium text-slate-400 uppercase tracking-widest mb-4">
            Plan a trip
          </h2>
          <form onSubmit={submit} className="space-y-4">
            <div className="space-y-2">
              <label className="text-xs text-slate-400 flex items-center gap-2">
                <PlayCircle className="w-3.5 h-3.5" /> Start (USA)
              </label>
              <Input
                data-testid="start-input"
                value={start}
                onChange={(e) => setStart(e.target.value)}
                placeholder="e.g., Los Angeles, CA"
                className="bg-slate-900 border-slate-700 text-slate-100 placeholder:text-slate-500"
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs text-slate-400 flex items-center gap-2">
                <Flag className="w-3.5 h-3.5" /> Finish (USA)
              </label>
              <Input
                data-testid="finish-input"
                value={finish}
                onChange={(e) => setFinish(e.target.value)}
                placeholder="e.g., Dallas, TX"
                className="bg-slate-900 border-slate-700 text-slate-100 placeholder:text-slate-500"
              />
            </div>
            <Button
              data-testid="plan-route-btn"
              type="submit"
              disabled={loading || !start || !finish}
              className="w-full bg-amber-400 hover:bg-amber-300 text-slate-900 font-semibold"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Calculating route…
                </>
              ) : (
                <>Find optimal route</>
              )}
            </Button>
          </form>

          {error && (
            <div
              data-testid="error-message"
              className="mt-4 p-3 rounded-md bg-red-950/60 border border-red-900 text-red-200 text-sm"
            >
              {error}
            </div>
          )}

          {data && (
            <div data-testid="results-panel" className="mt-6 space-y-4">
              <Card className="bg-slate-900 border-slate-800">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm text-slate-300">
                    Trip summary
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <Row
                    label="Distance"
                    value={`${data.route.distance_mi} mi`}
                  />
                  <Row
                    label="Drive time"
                    value={`${(data.route.duration_s / 3600).toFixed(1)} h`}
                  />
                  <Row
                    label="Total fuel"
                    value={`${data.fuel_plan.total_gallons} gal`}
                  />
                  <Separator className="bg-slate-800 my-2" />
                  <Row
                    label="Total fuel cost"
                    value={
                      <span
                        data-testid="total-cost"
                        className="text-amber-300 font-bold"
                      >
                        ${data.fuel_plan.total_cost_usd.toFixed(2)}
                      </span>
                    }
                  />
                  <Row
                    label="Refuel stops"
                    value={data.fuel_plan.stops.length}
                  />
                  <p className="text-xs text-slate-500 pt-2">
                    {data.fuel_plan.note}
                  </p>
                </CardContent>
              </Card>

              <div className="space-y-2">
                <h3 className="text-xs font-medium text-slate-400 uppercase tracking-widest">
                  Refuel stops
                </h3>
                {data.fuel_plan.stops.length === 0 ? (
                  <p className="text-sm text-slate-500">
                    No stops needed — within single tank.
                  </p>
                ) : (
                  data.fuel_plan.stops.map((s, i) => (
                    <Card
                      key={s.opis_id + i}
                      data-testid={`stop-card-${i}`}
                      className="bg-slate-900 border-slate-800"
                    >
                      <CardContent className="p-3">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex items-center gap-2">
                            <Badge className="bg-amber-400 text-slate-900 hover:bg-amber-300">
                              #{i + 1}
                            </Badge>
                            <div>
                              <p className="text-sm font-semibold leading-tight">
                                {s.name}
                              </p>
                              <p className="text-xs text-slate-400">
                                {s.city}, {s.state} · mile {s.mile_marker}
                              </p>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className="text-amber-300 font-bold text-sm">
                              ${s.price_per_gallon.toFixed(3)}
                            </p>
                            <p className="text-[11px] text-slate-500">/ gal</p>
                          </div>
                        </div>
                        <div className="grid grid-cols-2 gap-2 mt-3 text-xs text-slate-400">
                          <span>{s.gallons_purchased} gal</span>
                          <span className="text-right">
                            ${s.stop_cost_usd.toFixed(2)}
                          </span>
                        </div>
                      </CardContent>
                    </Card>
                  ))
                )}
              </div>
            </div>
          )}
        </section>

        {/* MAP */}
        <section className="relative h-[60vh] lg:h-auto">
          <MapContainer
            data-testid="route-map"
            center={center}
            zoom={5}
            style={{ height: "100%", width: "100%", minHeight: "500px" }}
            scrollWheelZoom
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {polyline.length > 0 && (
              <>
                <Polyline
                  positions={polyline}
                  pathOptions={{ color: "#f59e0b", weight: 5 }}
                />
                <FitBounds points={polyline} />
                <Marker
                  position={[data.start.lat, data.start.lng]}
                  icon={startIcon}
                >
                  <Popup>
                    <strong>Start:</strong> {data.start.label}
                  </Popup>
                </Marker>
                <Marker
                  position={[data.finish.lat, data.finish.lng]}
                  icon={finishIcon}
                >
                  <Popup>
                    <strong>Finish:</strong> {data.finish.label}
                  </Popup>
                </Marker>
                {data.fuel_plan.stops.map((s, i) => (
                  <Marker
                    key={s.opis_id + i}
                    position={[s.lat, s.lng]}
                    icon={fuelIcon}
                  >
                    <Popup>
                      <div style={{ minWidth: 180 }}>
                        <strong>
                          #{i + 1} {s.name}
                        </strong>
                        <br />
                        {s.city}, {s.state}
                        <br />
                        <span style={{ color: "#b45309" }}>
                          ${s.price_per_gallon.toFixed(3)} / gal
                        </span>
                        <br />
                        {s.gallons_purchased} gal · $
                        {s.stop_cost_usd.toFixed(2)}
                      </div>
                    </Popup>
                  </Marker>
                ))}
              </>
            )}
          </MapContainer>
          {!data && !loading && (
            <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
              <div className="bg-slate-900/85 border border-slate-800 px-5 py-3 rounded-lg text-sm text-slate-300 flex items-center gap-2">
                <MapPin className="w-4 h-4 text-amber-400" />
                Enter a start and finish to plan a route.
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex items-center justify-between text-slate-300">
      <span className="text-slate-400">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
