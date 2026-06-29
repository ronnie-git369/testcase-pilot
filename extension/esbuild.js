// esbuild build script for the extension host bundle.
//
// Why a bundler at all? VS Code loads ONE entry file (package.json "main").
// tsc emits a tree of CommonJS files; a bundler collapses our whole src/ tree
// (plus any npm deps) into a single dist/extension.js that loads fast. esbuild
// is used because it is ~100x faster than tsc for bundling and has first-class
// watch support.
//
// Two-track build: this script ONLY produces the shipped bundle. Type-checking
// and the Node unit tests still go through tsc (npm run compile-tests), so we
// keep real type safety while shipping a fast single-file bundle.

const esbuild = require("esbuild");

const production = process.argv.includes("--production");
const watch = process.argv.includes("--watch");

async function main() {
  const ctx = await esbuild.context({
    entryPoints: ["src/extension.ts"],
    bundle: true,
    outfile: "dist/extension.js",
    platform: "node", // the extension host is Node, not a browser
    format: "cjs", // VS Code requires CommonJS for the host bundle
    target: "node18", // VS Code 1.85 ships Node 18
    // `vscode` is injected by the host at runtime — it must NEVER be bundled.
    external: ["vscode"],
    sourcemap: !production, // map stack traces back to TS while developing
    minify: production, // smaller bundle for packaging
    logLevel: "info",
  });

  if (watch) {
    await ctx.watch();
    console.log("[esbuild] watching…");
  } else {
    await ctx.rebuild();
    await ctx.dispose();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
