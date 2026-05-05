import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import "./styles.css";
import App from "./App";
import { IngestPage } from "./pages/Ingest";
import { HermesPage } from "./pages/Hermes";

(() => {
  const stored = window.localStorage.getItem("theme");
  const initial =
    stored === "light" || stored === "dark"
      ? stored
      : window.matchMedia("(prefers-color-scheme: light)").matches
        ? "light"
        : "dark";
  document.documentElement.classList.toggle("dark", initial === "dark");
  document.documentElement.classList.toggle("light", initial === "light");
})();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/ingest" element={<IngestPage />} />
        <Route path="/p/:lie/hermes" element={<HermesPage />} />
        <Route path="/hermes" element={<HermesPage />} />
        <Route path="/p/:lie/*" element={<App />} />
        <Route path="/p/:lie" element={<App />} />
        <Route path="/" element={<App />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
