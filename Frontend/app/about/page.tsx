'use client'

import React from 'react';
import { useRouter } from 'next/navigation';

export default function AboutPage() 
{
    const router = useRouter();
    return (
        <div>
            <h1>About</h1>
            <p>ISAT Recruitment Tool
                is a chatbot that answers questions about the ISAT program
                To explore the ISAT Website, click the link below.
            </p>
            <a href = "https://www.jmu.edu/cise/isat/index.shtml"> ISAT Website</a>
            <br></br>
          <button className="button" onClick={() => router.push('/')}>
            Back to Home Page
          </button>
        </div>
    );
};

