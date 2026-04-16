import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';
import { existsSync } from 'fs';

export async function POST(request: NextRequest) {
  try {
    const { question, conversation_history } = await request.json();

    if (!question || typeof question !== 'string') {
      return NextResponse.json(
        { error: 'Question is required' },
        { status: 400 }
      );
    }

    // Validate conversation_history if provided
    const history = conversation_history || [];
    if (!Array.isArray(history)) {
      return NextResponse.json(
        { error: 'conversation_history must be an array' },
        { status: 400 }
      );
    }

    // Get project root (one level up from Frontend)
    const projectRoot = path.resolve(process.cwd(), '..');

    // Resolve Python executable in a robust order:
    // 1) Project-local venv names in project root (preferred for reproducibility)
    // 2) Active shell venv (VIRTUAL_ENV)
    // 3) System python3
    const findPython = () => {
      const venvNames = ['ISATRecruiter', 'venv', '.venv', 'env'];
      for (const name of venvNames) {
        const venvPython = path.join(projectRoot, name, 'bin', 'python');
        if (existsSync(venvPython)) {
          return venvPython;
        }
      }

      const virtualEnv = process.env.VIRTUAL_ENV;
      if (virtualEnv) {
        const venvPython = path.join(virtualEnv, 'bin', 'python');
        if (existsSync(venvPython)) return venvPython;
      }
      return 'python3';
    };
    const pythonExecutable = findPython();

    // Call Python function
    const result = await new Promise<{answer: string, conversation_history: any[]}>((resolve, reject) => {
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
conversation_history = json.loads(${JSON.stringify(JSON.stringify(history))})
answer, updated_history = process_question(question, conversation_history)
result = json.dumps({"answer": answer, "conversation_history": updated_history})
print(result, end='', flush=True)
      `.trim();

      const pythonProcess = spawn(pythonExecutable, ['-c', pythonCode], {
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
          try {
            const parsed = JSON.parse(output.trim());
            resolve(parsed);
          } catch (e) {
            // Fallback for backward compatibility
            resolve({ answer: output.trim(), conversation_history: [] });
          }
        }
      });

      pythonProcess.on('error', (error) => {
        reject(new Error(`Failed to start Python: ${error.message}`));
      });
    });

    return NextResponse.json({ 
      answer: result.answer, 
      conversation_history: result.conversation_history 
    });
  } catch (error: any) {
    return NextResponse.json(
      { error: error.message || 'Failed to process question' },
      { status: 500 }
    );
  }
}

