import { NextResponse } from "next/server";

type PredictRequest = {
  city?: string;
};

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export async function POST(request: Request) {
  let payload: PredictRequest;

  try {
    payload = (await request.json()) as PredictRequest;
  } catch {
    return NextResponse.json({ detail: "Invalid JSON payload." }, { status: 400 });
  }

  const city = payload.city?.trim();
  if (!city) {
    return NextResponse.json({ detail: "City is required." }, { status: 400 });
  }

  const apiBaseUrl =
    process.env.AQI_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL;

  try {
    const backendResponse = await fetch(`${apiBaseUrl}/predict`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ city }),
      cache: "no-store",
    });

    const backendPayload = await backendResponse.json().catch(() => ({
      detail: "Invalid backend response.",
    }));

    if (!backendResponse.ok) {
      return NextResponse.json(
        {
          detail:
            backendPayload?.detail || "AQI backend returned an error response.",
        },
        { status: backendResponse.status }
      );
    }

    return NextResponse.json(backendPayload, { status: 200 });
  } catch {
    return NextResponse.json(
      {
        detail:
          "Could not reach AQI backend. Ensure FastAPI is running and AQI_API_BASE_URL is correct.",
      },
      { status: 502 }
    );
  }
}
