#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');

async function testCLIIntegration() {
    console.log('🧪 Testing CrystaLyse CLI Integration');
    console.log('=' .repeat(50));
    
    // Test 1: Basic commands
    console.log('\n📋 Test 1: Basic CLI Commands');
    const commands = ['--help', '--version'];
    
    for (const cmd of commands) {
        try {
            const result = await runCommand([cmd]);
            console.log(`✅ Command '${cmd}' works`);
        } catch (error) {
            console.log(`❌ Command '${cmd}' failed:`, error.message);
        }
    }
    
    // Test 2: Python Bridge Connection
    console.log('\n📋 Test 2: Python Bridge Connection');
    const bridgeScript = path.join(__dirname, 'src/bridge/crystalyse_bridge.py');
    
    try {
        const pythonProcess = spawn('python3', [bridgeScript], {
            stdio: 'pipe',
            cwd: path.join(__dirname, '..')
        });
        
        let output = '';
        let hasReady = false;
        
        pythonProcess.stdout.on('data', (data) => {
            output += data.toString();
            if (output.includes('"type": "ready"')) {
                hasReady = true;
            }
        });
        
        pythonProcess.stderr.on('data', (data) => {
            console.error('Python stderr:', data.toString());
        });
        
        // Test a simple validation
        setTimeout(() => {
            pythonProcess.stdin.write('{"type": "validate", "composition": "LiFePO4"}\n');
        }, 1000);
        
        // Wait for response
        await new Promise((resolve) => {
            setTimeout(() => {
                pythonProcess.kill();
                
                if (hasReady) {
                    console.log('✅ Python bridge started successfully');
                } else {
                    console.log('❌ Python bridge failed to start');
                }
                
                if (output.includes('"type": "complete"')) {
                    console.log('✅ Bridge responds to commands');
                } else if (output.includes('demo')) {
                    console.log('⚠️  Bridge running in demo mode');
                } else {
                    console.log('❌ Bridge communication issue');
                }
                
                resolve();
            }, 3000);
        });
        
    } catch (error) {
        console.log('❌ Python bridge test failed:', error.message);
    }
    
    // Test 3: Interactive Shell Quick Test
    console.log('\n📋 Test 3: Interactive Shell Launch');
    try {
        const shellProcess = spawn('node', [path.join(__dirname, 'dist/index.js'), 'shell'], {
            stdio: 'pipe'
        });
        
        let shellOutput = '';
        let shellStarted = false;
        
        shellProcess.stdout.on('data', (data) => {
            shellOutput += data.toString();
            if (shellOutput.includes('CrystaLyse.AI') && shellOutput.includes('crystalyse >')) {
                shellStarted = true;
            }
        });
        
        // Wait a bit then exit
        await new Promise((resolve) => {
            setTimeout(() => {
                if (shellStarted) {
                    console.log('✅ Interactive shell starts correctly');
                } else {
                    console.log('❌ Interactive shell failed to start');
                }
                
                shellProcess.stdin.write('/exit\n');
                setTimeout(() => {
                    shellProcess.kill();
                    resolve();
                }, 500);
            }, 2000);
        });
        
    } catch (error) {
        console.log('❌ Shell test failed:', error.message);
    }
    
    console.log('\n✅ Integration test completed!');
}

function runCommand(args) {
    return new Promise((resolve, reject) => {
        const process = spawn('node', [path.join(__dirname, 'dist/index.js'), ...args], {
            stdio: 'pipe'
        });
        
        let output = '';
        process.stdout.on('data', (data) => {
            output += data.toString();
        });
        
        process.on('close', (code) => {
            if (code === 0) {
                resolve(output);
            } else {
                reject(new Error(`Process exited with code ${code}`));
            }
        });
        
        process.on('error', reject);
    });
}

// Run tests
testCLIIntegration().catch(console.error);