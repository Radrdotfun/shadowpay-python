// prove.js
import fs from "fs";
import { groth16 } from "snarkjs";

/**
 * Usage:
 *   node prove.js <zkeyPath> <wasmPath> <inputJsonPath>
 * Writes JSON to stdout: { proof, publicSignals }
 * On error writes JSON to stderr: { error: "message" } and exits(1)
 */
async function main() {
  try {
    const [zkeyPath, wasmPath, inputPath] = process.argv.slice(2);
    if (!zkeyPath || !wasmPath || !inputPath) {
      throw new Error("Usage: node prove.js <zkeyPath> <wasmPath> <inputJsonPath>");
    }

    // Load input
    const input = JSON.parse(fs.readFileSync(inputPath, "utf8"));

    // Generate proof (snarkjs can read files directly)
    const { proof, publicSignals } = await groth16.fullProve(input, wasmPath, zkeyPath);

    // Ensure BigInts are serialized as strings
    const stringifyBigInts = (o) =>
      typeof o === "bigint" ? o.toString() :
      Array.isArray(o) ? o.map(stringifyBigInts) :
      (o && typeof o === "object")
        ? Object.fromEntries(Object.entries(o).map(([k, v]) => [k, stringifyBigInts(v)]))
        : o;

    process.stdout.write(JSON.stringify({
      proof: stringifyBigInts(proof),
      publicSignals: stringifyBigInts(publicSignals)
    }));
  } catch (err) {
    process.stderr.write(JSON.stringify({ error: err?.message || String(err) }));
    process.exit(1);
  }
}

main();

