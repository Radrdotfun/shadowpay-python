/**
 * ShadowPay Prover Service
 * Node.js sidecar for ZK proof generation using snarkjs
 */

const express = require('express');
const cors = require('cors');
const snarkjs = require('snarkjs');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(cors());
app.use(express.json({ limit: '50mb' }));

// Circuit artifacts cache
const circuits = new Map();

/**
 * Load circuit artifacts
 */
async function loadCircuit(circuitType = 'spending') {
    if (circuits.has(circuitType)) {
        return circuits.get(circuitType);
    }

    const circuitDir = process.env.CIRCUIT_DIR || path.join(__dirname, 'circuits');
    const wasmPath = path.join(circuitDir, `${circuitType}.wasm`);
    const zkeyPath = path.join(circuitDir, `${circuitType}_final.zkey`);

    try {
        console.log(`Loading circuit artifacts for ${circuitType}...`);
        
        // Check if files exist
        if (!fs.existsSync(wasmPath)) {
            throw new Error(`WASM file not found: ${wasmPath}`);
        }
        if (!fs.existsSync(zkeyPath)) {
            throw new Error(`ZKey file not found: ${zkeyPath}`);
        }

        const circuit = {
            wasm: wasmPath,
            zkey: zkeyPath,
        };

        circuits.set(circuitType, circuit);
        console.log(`Circuit ${circuitType} loaded successfully`);
        return circuit;

    } catch (error) {
        console.error(`Failed to load circuit ${circuitType}:`, error.message);
        throw error;
    }
}

/**
 * Health check endpoint
 */
app.get('/health', (req, res) => {
    res.json({
        status: 'ok',
        service: 'shadowpay-prover',
        version: '1.0.0',
        loadedCircuits: Array.from(circuits.keys()),
    });
});

/**
 * Generate ZK proof
 */
app.post('/prove', async (req, res) => {
    try {
        const { input, circuitType = 'spending' } = req.body;

        if (!input) {
            return res.status(400).json({ error: 'Missing input parameter' });
        }

        console.log(`Generating proof for circuit: ${circuitType}`);
        const startTime = Date.now();

        // Load circuit artifacts
        const circuit = await loadCircuit(circuitType);

        // Generate proof using snarkjs
        const { proof, publicSignals } = await snarkjs.groth16.fullProve(
            input,
            circuit.wasm,
            circuit.zkey
        );

        const duration = Date.now() - startTime;
        console.log(`Proof generated in ${duration}ms`);

        res.json({
            proof,
            publicSignals,
            metadata: {
                circuitType,
                duration,
                timestamp: Date.now(),
            },
        });

    } catch (error) {
        console.error('Proof generation failed:', error);
        res.status(500).json({
            error: error.message,
            stack: process.env.NODE_ENV === 'development' ? error.stack : undefined,
        });
    }
});

/**
 * Verify ZK proof
 */
app.post('/verify', async (req, res) => {
    try {
        const { proof, publicSignals, circuitType = 'spending' } = req.body;

        if (!proof || !publicSignals) {
            return res.status(400).json({ error: 'Missing proof or publicSignals' });
        }

        console.log(`Verifying proof for circuit: ${circuitType}`);
        const startTime = Date.now();

        // Load verification key
        const circuit = await loadCircuit(circuitType);
        const vKeyPath = circuit.zkey.replace('_final.zkey', '_verification_key.json');
        
        let vKey;
        if (fs.existsSync(vKeyPath)) {
            vKey = JSON.parse(fs.readFileSync(vKeyPath, 'utf8'));
        } else {
            // Extract verification key from zkey
            vKey = await snarkjs.zKey.exportVerificationKey(circuit.zkey);
        }

        // Verify proof
        const isValid = await snarkjs.groth16.verify(vKey, publicSignals, proof);

        const duration = Date.now() - startTime;
        console.log(`Proof verified in ${duration}ms: ${isValid}`);

        res.json({
            valid: isValid,
            metadata: {
                circuitType,
                duration,
                timestamp: Date.now(),
            },
        });

    } catch (error) {
        console.error('Proof verification failed:', error);
        res.status(500).json({
            error: error.message,
            stack: process.env.NODE_ENV === 'development' ? error.stack : undefined,
        });
    }
});

/**
 * Get supported circuits
 */
app.get('/circuits', (req, res) => {
    const circuitDir = process.env.CIRCUIT_DIR || path.join(__dirname, 'circuits');
    
    try {
        if (!fs.existsSync(circuitDir)) {
            return res.json({ circuits: [] });
        }

        const files = fs.readdirSync(circuitDir);
        const wasmFiles = files.filter(f => f.endsWith('.wasm'));
        const availableCircuits = wasmFiles.map(f => f.replace('.wasm', ''));

        res.json({
            circuits: availableCircuits,
            loaded: Array.from(circuits.keys()),
            circuitDir,
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

/**
 * Start server
 */
app.listen(PORT, () => {
    console.log(`🚀 ShadowPay Prover Service running on port ${PORT}`);
    console.log(`   Health check: http://localhost:${PORT}/health`);
    console.log(`   Prove:        POST http://localhost:${PORT}/prove`);
    console.log(`   Verify:       POST http://localhost:${PORT}/verify`);
    console.log(`   Circuits:     GET http://localhost:${PORT}/circuits`);
    console.log('');
    console.log('Environment:');
    console.log(`   NODE_ENV:     ${process.env.NODE_ENV || 'production'}`);
    console.log(`   CIRCUIT_DIR:  ${process.env.CIRCUIT_DIR || path.join(__dirname, 'circuits')}`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
    console.log('SIGTERM signal received: closing HTTP server');
    process.exit(0);
});

process.on('SIGINT', () => {
    console.log('SIGINT signal received: closing HTTP server');
    process.exit(0);
});

