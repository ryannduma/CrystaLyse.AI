#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');

async function testInteractiveShell() {
    console.log('🧪 Testing CrystaLyse Interactive Shell');
    console.log('=' .repeat(50));
    
    const shellProcess = spawn('node', [path.join(__dirname, 'dist/index.js'), 'shell'], {
        stdio: 'pipe'
    });
    
    let output = '';
    shellProcess.stdout.on('data', (data) => {
        const text = data.toString();
        output += text;
        process.stdout.write(text); // Show output in real-time
    });
    
    shellProcess.stderr.on('data', (data) => {
        console.error('STDERR:', data.toString());
    });
    
    // Wait a bit for shell to start
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    console.log('\\n📝 Sending test commands to shell...');
    
    // Test commands
    const testCommands = [
        '/help',
        '/status',
        '/mode rigorous',
        'Design a battery cathode material',
        '/history',
        '/exit'
    ];
    
    for (const command of testCommands) {
        console.log(`\\n> ${command}`);
        shellProcess.stdin.write(command + '\\n');
        await new Promise(resolve => setTimeout(resolve, 2000));
    }
    
    // Give it time to complete
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    shellProcess.kill();
    
    console.log('\\n✅ Interactive shell test completed');
    
    // Analyze output
    if (output.includes('CrystaLyse.AI')) {
        console.log('✅ Shell banner displayed correctly');
    }
    
    if (output.includes('crystalyse >')) {
        console.log('✅ Shell prompt working');
    }
    
    if (output.includes('Commands:')) {
        console.log('✅ Help system functional');
    }
    
    return output;
}

// Run the test
if (require.main === module) {
    testInteractiveShell().catch(console.error);
}

module.exports = { testInteractiveShell };