import { defineConfig, type Plugin } from "vite";
import { build as esbuild } from "esbuild";
import { writeFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(HERE, "../spire_of_ash/web/static");

/** Routes the Python server owns. Everything else is client assets. */
const API = ["/state", "/action", "/piles", "/records", "/classes", "/abandon"];

/**
 * Emit art-manifest.json listing every sprite id the client can draw.
 *
 * tests/test_content.py asserts every monster key appears here, so a monster
 * added to the Python tables without art fails the suite instead of silently
 * rendering as a generic blob. The old test string-sliced app.js; this bundles
 * and evaluates the registry instead, so it survives any refactor.
 */
function artManifest(): Plugin {
  return {
    name: "spire-art-manifest",
    apply: "build",
    async closeBundle() {
      const entry = resolve(HERE, "src/art/registry.ts");
      const bundled = await esbuild({
        entryPoints: [entry],
        bundle: true,
        format: "esm",
        platform: "neutral",
        write: false,
      });
      const code = bundled.outputFiles[0]!.text;
      const mod = await import(
        "data:text/javascript;base64," + Buffer.from(code).toString("base64")
      );
      writeFileSync(
        resolve(OUT, "art-manifest.json"),
        JSON.stringify(mod.manifest(), null, 2) + "\n",
      );
    },
  };
}

export default defineConfig(({ command }) => ({
  root: HERE,
  // Python serves index.html at "/" but assets out of "/static/".
  base: command === "build" ? "/static/" : "/",
  plugins: [artManifest()],
  build: {
    outDir: OUT,
    emptyOutDir: true,
    target: "es2022",
    sourcemap: true,
  },
  server: {
    port: 5173,
    proxy: Object.fromEntries(
      API.map((path) => [path, { target: "http://127.0.0.1:8765", changeOrigin: false }]),
    ),
  },
}));
