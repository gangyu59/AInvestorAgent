import { useEffect, useMemo, useState } from "react";
import HomePage from "./routes/index";
import StockPage from "./routes/stock";
import PortfolioPage from "./routes/portfolio";
import SimulatorPage from "./routes/simulator";
import HistoricalSimulatorPage from "./routes/historical_simulator"; // 🆕 添加
import MonitorPage from "./routes/monitor";
import ManagePage from "./routes/manage";
import TradingPage from "./routes/trading";

// 🆕 添加 historical-simulator 类型
type Route = "home" | "stock" | "portfolio" | "simulator" | "historical-simulator" | "monitor" | "manage" | "trading";

function parseRoute(hash: string): { route: Route; query?: Record<string, string> } {
  const h = (hash || "").replace(/^#\/?/, "");
  const [path, qs] = h.split("?");
  const route = (path || "").trim() as Route;
  const query = Object.fromEntries(new URLSearchParams(qs || ""));

  switch (route) {
    case "stock":
    case "portfolio":
    case "simulator":
    case "historical-simulator": // 🆕 添加这行
    case "monitor":
    case "manage":
    case "trading":
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
      case "stock":
        return <StockPage query={query} />;
      case "portfolio":
        return <PortfolioPage />;
      case "simulator":
        return <SimulatorPage />;
      case "historical-simulator": // 🆕 添加这个 case
        return <HistoricalSimulatorPage />;
      case "monitor":
        return <MonitorPage />;
      case "manage":
        return <ManagePage />;
      case "trading":
        return <TradingPage />;
      default:
        return <HomePage />;
    }
  }, [route, query]);

  return page;
}