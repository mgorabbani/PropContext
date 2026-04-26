import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import App from "./App";
import { IngestPage } from "./pages/Ingest";

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

const Root = window.location.pathname.startsWith("/ingest") ? IngestPage : App;

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Root />
  </StrictMode>,
);
