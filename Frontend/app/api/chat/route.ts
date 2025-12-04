import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';

export async function POST(request: NextRequest) {
  try {
    const { question } = await request.json();

    if (!question || typeof question !== 'string') {
      return NextResponse.json(
        { error: 'Question is required' },
        { status: 400 }
      );
    }

    // Get project root (one level up from Frontend)
    const projectRoot = path.resolve(process.cwd(), '..');

    // Call Python function
    const result = await new Promise<string>((resolve, reject) => {
      const pythonCode = `
import sys
import os
import json

# Add project root to path
project_root = r'${projectRoot.replace(/\\/g, '/')}'
sys.path.insert(0, project_root)
os.chdir(project_root)

# Import and call function
from LangGraph.main import process_question
question = json.loads(${JSON.stringify(JSON.stringify(question))})
answer = process_question(question)
print(answer, end='', flush=True)
      `.trim();

      const pythonProcess = spawn('python3', ['-c', pythonCode], {
        cwd: projectRoot,
        env: { ...process.env, PYTHONUNBUFFERED: '1' }
      });

      let output = '';
      let errorOutput = '';

      pythonProcess.stdout.on('data', (data) => {
        output += data.toString();
      });

      pythonProcess.stderr.on('data', (data) => {
        const stderrData = data.toString();
        errorOutput += stderrData;
        // Log stderr to console (for chunk retrieval debug output)
        console.error(stderrData);
      });

      pythonProcess.on('close', (code) => {
        if (code !== 0) {
          reject(new Error(errorOutput || `Process exited with code ${code}`));
        } else {
          resolve(output.trim());
        }
      });

      pythonProcess.on('error', (error) => {
        reject(new Error(`Failed to start Python: ${error.message}`));
      });
    });

    return NextResponse.json({ answer: result });
  } catch (error: any) {
    return NextResponse.json(
      { error: error.message || 'Failed to process question' },
      { status: 500 }
    );
  }
}

