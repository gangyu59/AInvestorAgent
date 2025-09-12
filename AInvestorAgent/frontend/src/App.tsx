// frontend/src/App.tsx
import * as React from "react";
import StockPage from "./routes/stock";

export default function App() {
  return <StockPage />;
}


// 其他 import 之后追加：
import MonitorPage from "./routes/monitor";
import ManagePage from "./routes/manage";

// <Routes> ... </Routes> 内追加：
<Route path="/monitor" element={<MonitorPage />} />
<Route path="/manage" element={<ManagePage />} />
