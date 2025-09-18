import { useEffect, useMemo, useState } from "react";
import HomePage from "./routes/index";
import StockPage from "./routes/stock";
import PortfolioPage from "./routes/portfolio";
import SimulatorPage from "./routes/simulator";
import MonitorPage from "./routes/monitor";
import ManagePage from "./routes/manage";

type Route = "home" | "stock" | "portfolio" | "simulator" | "monitor" | "manage";

function parseRoute(hash: string): { route: Route; query?: Record<string, string> } {
  const h = (hash || "").replace(/^#\/?/, ""); // e.g., "stock?query=AAPL"
  const [path, qs] = h.split("?");
  const route = (path || "").trim() as Route;
  const query = Object.fromEntries(new URLSearchParams(qs || ""));
  switch (route) {
    case "stock":
    case "portfolio":
    case "simulator":
    case "monitor":
    case "manage":
      return { route, query };
    default:
      return { route: "home" };
  }
}

export default function App() {
  const [{ route, query }, setLoc] = useState(parseRoute(window.location.hash));

  useEffect(() => {
    const onHash = () => setLoc(parseRoute(window.location.hash));
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const page = useMemo(() => {
    switch (route) {
      case "stock": return <StockPage query={query} />;
      case "portfolio": return <PortfolioPage />;
      case "simulator": return <SimulatorPage />;
      case "monitor": return <MonitorPage />;
      case "manage": return <ManagePage />;
      default: return <HomePage />;
    }
  }, [route, query]);

  return page;
}
