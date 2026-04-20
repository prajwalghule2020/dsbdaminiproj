"use client";

import { FormEvent, useMemo, useState } from "react";
import type { LucideIcon } from "lucide-react";
import {
  Activity,
  AlertTriangle,
  CalendarDays,
  CheckCircle2,
  Clock3,
  Database,
  Gauge,
  Loader2,
  MapPin,
  Route,
  Server,
  Sparkles,
  Timer,
  Wind,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  CardAction,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";

type PredictResponse = {
  city: string;
  predicted_aqi: number;
  category: string;
  prediction_for_date: string;
  diagnostics: {
    history_start_utc: string;
    history_end_utc: string;
    hourly_rows_used: number;
    daily_rows_built: number;
    imputed_fields: string[];
  };
};

type ExecutionDetails = {
  endpoint: string;
  method: "POST";
  statusCode: number | null;
  durationMs: number;
  startedAt: string;
  completedAt: string;
  success: boolean;
};

const CATEGORY_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  Good: "default",
  Satisfactory: "secondary",
  Moderate: "outline",
  Poor: "destructive",
  "Very Poor": "destructive",
  Severe: "destructive",
};

const CATEGORY_BAR_COLOR: Record<string, string> = {
  Good: "bg-emerald-500",
  Satisfactory: "bg-cyan-500",
  Moderate: "bg-amber-500",
  Poor: "bg-orange-500",
  "Very Poor": "bg-rose-500",
  Severe: "bg-red-600",
};

const QUICK_CITIES = ["Delhi", "Mumbai", "Chennai", "Kolkata", "Bangalore"];

const PIPELINE_STEPS: Array<{ label: string; detail: string; icon: LucideIcon }> = [
  {
    label: "City Resolution",
    detail: "Geocoding maps city name to latitude and longitude.",
    icon: MapPin,
  },
  {
    label: "Pollution Ingestion",
    detail: "Backend fetches history and automatically falls back to forecast when required.",
    icon: Database,
  },
  {
    label: "Feature Engineering",
    detail: "24h rolling daily means and lag features are generated for inference.",
    icon: Route,
  },
  {
    label: "AQI Inference",
    detail: "Linear Regression predicts next-day AQI and maps CPCB category.",
    icon: Gauge,
  },
];

function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "N/A";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "N/A";
  }

  return parsed.toLocaleString("en-IN", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function MetricTile({
  label,
  value,
  hint,
  icon: Icon,
}: {
  label: string;
  value: string;
  hint?: string;
  icon: LucideIcon;
}) {
  return (
    <div className="rounded-xl border border-border/70 bg-background/70 p-3">
      <p className="flex items-center gap-2 text-xs uppercase tracking-wide text-muted-foreground">
        <Icon className="size-3.5" />
        {label}
      </p>
      <p className="mt-2 text-base font-semibold text-foreground">{value}</p>
      {hint ? <p className="mt-1 text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

export default function Home() {
  const [city, setCity] = useState("Delhi");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [execution, setExecution] = useState<ExecutionDetails | null>(null);

  const categoryVariant = useMemo(() => {
    if (!result) {
      return "outline" as const;
    }
    return CATEGORY_VARIANT[result.category] ?? "outline";
  }, [result]);

  const severityPercent = useMemo(() => {
    if (!result) {
      return 0;
    }

    const bounded = Math.max(0, Math.min(500, result.predicted_aqi));
    return Math.round((bounded / 500) * 100);
  }, [result]);

  const coverageDetails = useMemo(() => {
    if (!result) {
      return null;
    }

    const startMs = Date.parse(result.diagnostics.history_start_utc);
    const endMs = Date.parse(result.diagnostics.history_end_utc);
    if (Number.isNaN(startMs) || Number.isNaN(endMs) || endMs < startMs) {
      return null;
    }

    const expectedHours = Math.max(1, Math.round((endMs - startMs) / 3_600_000) + 1);
    const coverageRaw = (result.diagnostics.hourly_rows_used / expectedHours) * 100;
    const coverage = Math.round(Math.max(0, Math.min(100, coverageRaw)) * 10) / 10;

    return {
      expectedHours,
      coverage,
    };
  }, [result]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedCity = city.trim();
    if (!trimmedCity) {
      return;
    }

    const startedAt = new Date();
    const startedPerf = performance.now();
    let statusCode: number | null = null;
    let success = false;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/predict", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ city: trimmedCity }),
      });
      statusCode = response.status;

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.detail || "Prediction request failed.");
      }

      success = true;
      setResult(payload as PredictResponse);
    } catch (requestError) {
      const message =
        requestError instanceof Error
          ? requestError.message
          : "Something went wrong while fetching prediction.";
      setError(message);
      setResult(null);
    } finally {
      const completedAt = new Date();
      const durationMs = Math.max(1, Math.round(performance.now() - startedPerf));

      setExecution({
        endpoint: "/api/predict",
        method: "POST",
        statusCode,
        durationMs,
        startedAt: startedAt.toISOString(),
        completedAt: completedAt.toISOString(),
        success,
      });
      setLoading(false);
    }
  }

  return (
    <main className="relative isolate min-h-screen overflow-hidden px-4 py-8 sm:px-6 lg:px-10">
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_15%_15%,rgba(34,211,238,0.16),transparent_30%),radial-gradient(circle_at_85%_20%,rgba(14,165,233,0.1),transparent_25%),radial-gradient(circle_at_60%_95%,rgba(148,163,184,0.14),transparent_35%)]" />

      <div className="mx-auto w-full max-w-7xl space-y-6">
        <Card className="border-border/70 bg-card/85 backdrop-blur">
          <CardHeader className="gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div className="space-y-1.5">
              <p className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-muted-foreground">
                <Sparkles className="size-3.5" />
                Air Quality Intelligence Panel
              </p>
              <CardTitle className="text-2xl sm:text-3xl">AQI Next-Day Forecast Dashboard</CardTitle>
              <CardDescription>
                Analyze live prediction results, model diagnostics, and backend execution details in one
                view.
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="border-cyan-400/30 bg-cyan-500/10 text-cyan-200">
                <Server className="size-3" />
                API Ready
              </Badge>
              {execution ? (
                <Badge variant={execution.success ? "secondary" : "destructive"}>
                  {execution.success ? <CheckCircle2 className="size-3" /> : <AlertTriangle className="size-3" />}
                  {execution.success ? "Last Request Succeeded" : "Last Request Failed"}
                </Badge>
              ) : null}
            </div>
          </CardHeader>
        </Card>

        <div className="grid gap-6 lg:grid-cols-[340px_minmax(0,1fr)]">
          <div className="space-y-6">
            <Card className="border-border/70 bg-card/85 backdrop-blur">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Wind className="size-4" />
                  Prediction Controls
                </CardTitle>
                <CardDescription>Choose a city and run a fresh AQI forecast request.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <form className="space-y-3" onSubmit={onSubmit}>
                  <div className="space-y-2">
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">City</p>
                    <Input
                      value={city}
                      onChange={(event) => setCity(event.target.value)}
                      placeholder="Delhi"
                      aria-label="City"
                      className="h-10"
                    />
                  </div>

                  <Button type="submit" disabled={loading || city.trim().length === 0} className="h-10 w-full">
                    {loading ? (
                      <>
                        <Loader2 className="size-4 animate-spin" />
                        Running Forecast
                      </>
                    ) : (
                      <>
                        <Activity className="size-4" />
                        Run Prediction
                      </>
                    )}
                  </Button>
                </form>

                <Separator />

                <div className="space-y-2">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Quick Picks</p>
                  <div className="flex flex-wrap gap-2">
                    {QUICK_CITIES.map((quickCity) => (
                      <Button
                        key={quickCity}
                        type="button"
                        size="sm"
                        variant={city.toLowerCase() === quickCity.toLowerCase() ? "secondary" : "outline"}
                        onClick={() => setCity(quickCity)}
                      >
                        {quickCity}
                      </Button>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-border/70 bg-card/85 backdrop-blur">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Timer className="size-4" />
                  Execution Details
                </CardTitle>
                <CardDescription>Telemetry from the most recent API call.</CardDescription>
              </CardHeader>
              <CardContent>
                {execution ? (
                  <div className="grid gap-3">
                    <MetricTile
                      label="Request"
                      value={`${execution.method} ${execution.endpoint}`}
                      hint="Frontend route handler"
                      icon={Route}
                    />
                    <MetricTile
                      label="Status"
                      value={execution.statusCode ? String(execution.statusCode) : "N/A"}
                      hint={execution.success ? "Completed successfully" : "Returned an error"}
                      icon={Server}
                    />
                    <MetricTile
                      label="Latency"
                      value={`${execution.durationMs} ms`}
                      hint="Request round-trip"
                      icon={Clock3}
                    />
                    <MetricTile
                      label="Started"
                      value={formatDateTime(execution.startedAt)}
                      icon={CalendarDays}
                    />
                    <MetricTile
                      label="Completed"
                      value={formatDateTime(execution.completedAt)}
                      icon={CheckCircle2}
                    />
                  </div>
                ) : (
                  <p className="rounded-xl border border-dashed border-border/70 bg-background/60 px-3 py-6 text-sm text-muted-foreground">
                    Run a forecast to capture execution metrics.
                  </p>
                )}
              </CardContent>
            </Card>

            <Card className="border-border/70 bg-card/85 backdrop-blur">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="size-4" />
                  Pipeline Overview
                </CardTitle>
                <CardDescription>Core backend execution flow used by this model.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {PIPELINE_STEPS.map(({ label, detail, icon: Icon }) => (
                  <div key={label} className="rounded-xl border border-border/70 bg-background/70 p-3">
                    <p className="flex items-center gap-2 text-sm font-medium">
                      <Icon className="size-4 text-muted-foreground" />
                      {label}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            <Card className="border-border/70 bg-card/90 backdrop-blur">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-xl">
                  <Gauge className="size-5" />
                  Forecast Summary
                </CardTitle>
                <CardAction>
                  {result ? (
                    <Badge variant={categoryVariant}>{result.category}</Badge>
                  ) : (
                    <Badge variant="outline">Awaiting Prediction</Badge>
                  )}
                </CardAction>
                <CardDescription>
                  Central view of predicted AQI, severity profile, and prediction target date.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-5">
                {error ? (
                  <div className="rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                    <p className="flex items-center gap-2 font-medium">
                      <AlertTriangle className="size-4" />
                      Prediction Error
                    </p>
                    <p className="mt-1 text-destructive/90">{error}</p>
                  </div>
                ) : null}

                {result ? (
                  <>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div className="rounded-2xl border border-border/70 bg-background/70 p-4">
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">Predicted AQI</p>
                        <p className="mt-2 text-4xl font-semibold tracking-tight">{result.predicted_aqi.toFixed(2)}</p>
                        <p className="mt-1 text-xs text-muted-foreground">Forecast for {result.city}</p>
                      </div>
                      <div className="rounded-2xl border border-border/70 bg-background/70 p-4">
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">Target Date</p>
                        <p className="mt-2 flex items-center gap-2 text-lg font-semibold">
                          <CalendarDays className="size-4 text-muted-foreground" />
                          {result.prediction_for_date}
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground">CPCB category: {result.category}</p>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-xs uppercase tracking-wide text-muted-foreground">
                        <span>Relative Severity</span>
                        <span>{severityPercent}% of 500 AQI scale</span>
                      </div>
                      <div className="h-2 rounded-full bg-muted/70">
                        <div
                          className={`h-2 rounded-full ${CATEGORY_BAR_COLOR[result.category] ?? "bg-primary"}`}
                          style={{ width: `${severityPercent}%` }}
                        />
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="rounded-2xl border border-dashed border-border/70 bg-background/60 p-8 text-center">
                    <p className="text-sm text-muted-foreground">
                      No prediction yet. Use the control panel to generate an AQI forecast.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>

            <div className="grid gap-6 xl:grid-cols-2">
              <Card className="border-border/70 bg-card/85 backdrop-blur">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Database className="size-4" />
                    Data Diagnostics
                  </CardTitle>
                  <CardDescription>Backend history window and row-level data usage.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {result ? (
                    <>
                      <MetricTile label="City" value={result.city} icon={MapPin} />
                      <MetricTile
                        label="History Start"
                        value={formatDateTime(result.diagnostics.history_start_utc)}
                        icon={Clock3}
                      />
                      <MetricTile
                        label="History End"
                        value={formatDateTime(result.diagnostics.history_end_utc)}
                        icon={Clock3}
                      />
                      <div className="grid grid-cols-2 gap-3">
                        <MetricTile
                          label="Hourly Rows"
                          value={String(result.diagnostics.hourly_rows_used)}
                          icon={Database}
                        />
                        <MetricTile
                          label="Daily Rows"
                          value={String(result.diagnostics.daily_rows_built)}
                          icon={CalendarDays}
                        />
                      </div>
                    </>
                  ) : (
                    <p className="rounded-xl border border-dashed border-border/70 bg-background/60 px-3 py-6 text-sm text-muted-foreground">
                      Diagnostics become available after a successful prediction.
                    </p>
                  )}
                </CardContent>
              </Card>

              <Card className="border-border/70 bg-card/85 backdrop-blur">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Activity className="size-4" />
                    Model Quality Signals
                  </CardTitle>
                  <CardDescription>Quick indicators about feature completeness and imputations.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {result ? (
                    <>
                      <MetricTile
                        label="Imputed Fields"
                        value={String(result.diagnostics.imputed_fields.length)}
                        hint="Lower is generally better"
                        icon={AlertTriangle}
                      />

                      <div className="space-y-2 rounded-xl border border-border/70 bg-background/70 p-3">
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">Imputed Pollutants</p>
                        <div className="flex flex-wrap gap-2">
                          {result.diagnostics.imputed_fields.length > 0 ? (
                            result.diagnostics.imputed_fields.map((field) => (
                              <Badge key={field} variant="outline" className="border-amber-500/30 bg-amber-500/10 text-amber-200">
                                {field}
                              </Badge>
                            ))
                          ) : (
                            <Badge variant="secondary">
                              <CheckCircle2 className="size-3" />
                              None
                            </Badge>
                          )}
                        </div>
                      </div>

                      <div className="space-y-2 rounded-xl border border-border/70 bg-background/70 p-3">
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">History Coverage</p>
                        {coverageDetails ? (
                          <>
                            <p className="text-sm font-medium">
                              {coverageDetails.coverage}% ({result.diagnostics.hourly_rows_used}/{coverageDetails.expectedHours} hours)
                            </p>
                            <div className="h-2 rounded-full bg-muted/70">
                              <div
                                className="h-2 rounded-full bg-cyan-500"
                                style={{ width: `${coverageDetails.coverage}%` }}
                              />
                            </div>
                          </>
                        ) : (
                          <p className="text-sm text-muted-foreground">Coverage not available.</p>
                        )}
                      </div>
                    </>
                  ) : (
                    <p className="rounded-xl border border-dashed border-border/70 bg-background/60 px-3 py-6 text-sm text-muted-foreground">
                      Run one forecast to inspect imputation and history coverage details.
                    </p>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
