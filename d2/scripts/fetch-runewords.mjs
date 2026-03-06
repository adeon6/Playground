import { mkdir, writeFile } from "node:fs/promises";

const BASE_URL = "https://www.d2r-reimagined.com";
const OUTPUT_DIR = new URL("../public/data/", import.meta.url);
const OUTPUT_FILE = new URL("../public/data/runewords.json", import.meta.url);

async function fetchText(url) {
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch ${url}: ${response.status} ${response.statusText}`);
  }

  return response.text();
}

function getIndexScriptPath(html) {
  const match = html.match(/<script type="module" crossorigin src="([^"]+)"><\/script>/i);

  if (!match) {
    throw new Error("Could not find the site index script.");
  }

  return match[1];
}

function getRunewordChunkPaths(indexScript) {
  const matches = [...indexScript.matchAll(/assets\/runewords-[^"']+\.js/g)];
  const unique = [...new Set(matches.map((match) => match[0]))];

  if (unique.length === 0) {
    throw new Error("Could not find any runeword chunks.");
  }

  return unique;
}

function extractJsonText(chunkSource) {
  const match = chunkSource.match(/JSON\.parse\(`([\s\S]*?)`\)/);

  return match ? match[1] : null;
}

async function main() {
  const homepage = await fetchText(BASE_URL);
  const indexScriptPath = getIndexScriptPath(homepage);
  const indexScript = await fetchText(new URL(indexScriptPath, BASE_URL));
  const chunkPaths = getRunewordChunkPaths(indexScript);

  let jsonText = null;

  for (const chunkPath of chunkPaths) {
    const chunkSource = await fetchText(new URL(chunkPath, BASE_URL));
    jsonText = extractJsonText(chunkSource);

    if (jsonText) {
      break;
    }
  }

  if (!jsonText) {
    throw new Error("Found runeword chunks, but none contained the JSON payload.");
  }

  const parsed = JSON.parse(jsonText);
  await mkdir(OUTPUT_DIR, { recursive: true });
  await writeFile(OUTPUT_FILE, `${JSON.stringify(parsed, null, 2)}\n`);

  console.log(`Saved ${parsed.length} runewords to ${OUTPUT_FILE.pathname}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
