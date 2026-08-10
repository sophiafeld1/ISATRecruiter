import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';
import { existsSync } from 'fs';

async function callRemoteBackend(
  question: string,
  history: Array<{ role: string; content: string }>
) {
  const backendUrl = (process.env.BACKEND_URL || process.env.PYTHON_BACKEND_URL || '').replace(
    /\/$/,
    ''
  );
  if (!backendUrl) {
    return null;
  }

  const response = await fetch(`${backendUrl}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, conversation_history: history }),
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message =
      typeof payload.error === 'string'
        ? payload.error
        : typeof payload.detail === 'string'
          ? payload.detail
          : `Backend request failed (${response.status})`;
    throw new Error(message);
  }

  return payload as { answer: string; conversation_history: Array<{ role: string; content: string }> };
}

async function callLocalPython(
  question: string,
  history: Array<{ role: string; content: string }>
) {
  const projectRoot = path.resolve(process.cwd(), '..');

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

  return new Promise<{ answer: string; conversation_history: Array<{ role: string; content: string }> }>(
    (resolve, reject) => {
      const pythonCode = `
import sys
import os
import json

project_root = r'${projectRoot.replace(/\\/g, '/')}'
sys.path.insert(0, project_root)
os.chdir(project_root)

from LangGraph.main import process_question
question = json.loads(${JSON.stringify(JSON.stringify(question))})
conversation_history = json.loads(${JSON.stringify(JSON.stringify(history))})
answer, updated_history = process_question(question, conversation_history)
result = json.dumps({"answer": answer, "conversation_history": updated_history})
print(result, end='', flush=True)
      `.trim();

      const pythonProcess = spawn(pythonExecutable, ['-c', pythonCode], {
        cwd: projectRoot,
        env: { ...process.env, PYTHONUNBUFFERED: '1' },
      });

      let output = '';
      let errorOutput = '';

      pythonProcess.stdout.on('data', (data) => {
        output += data.toString();
      });

      pythonProcess.stderr.on('data', (data) => {
        const stderrData = data.toString();
        errorOutput += stderrData;
        console.error(stderrData);
      });

      pythonProcess.on('close', (code) => {
        if (code !== 0) {
          reject(new Error(errorOutput || `Process exited with code ${code}`));
          return;
        }

        try {
          resolve(JSON.parse(output.trim()));
        } catch {
          resolve({ answer: output.trim(), conversation_history: [] });
        }
      });

      pythonProcess.on('error', (error) => {
        reject(new Error(`Failed to start Python: ${error.message}`));
      });
    }
  );
}

export async function POST(request: NextRequest) {
  try {
    const { question, conversation_history } = await request.json();

    if (!question || typeof question !== 'string') {
      return NextResponse.json({ error: 'Question is required' }, { status: 400 });
    }

    const history = conversation_history || [];
    if (!Array.isArray(history)) {
      return NextResponse.json(
        { error: 'conversation_history must be an array' },
        { status: 400 }
      );
    }

    const result =
      (await callRemoteBackend(question, history)) ??
      (await callLocalPython(question, history));

    return NextResponse.json({
      answer: result.answer,
      conversation_history: result.conversation_history,
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to process question';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
