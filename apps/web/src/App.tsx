import { useEffect, useState } from "react";
import { Button } from "@steadydancer/ts-ui";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export function App() {
  const [health, setHealth] = useState<string>("unknown");

  useEffect(() => {
    async function fetchHealth() {
      try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const data = (await response.json()) as { status?: string };
        setHealth(data.status ?? "ok");
      } catch (error) {
        console.error("Failed to fetch health:", error);
        setHealth("error");
      }
    }

    void fetchHealth();
  }, []);

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: "1rem",
        fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
      }}
    >
      <h1>SteadyDancer Web</h1>
      <p>API health: {health}</p>
      <Button
        label="Test Button"
        onClick={() => {
          // eslint-disable-next-line no-alert
          alert("SteadyDancer UI is ready.");
        }}
      />
    </div>
  );
}

