'use client'

import { useRouter } from 'next/navigation';

export default function AboutPage() {
  const router = useRouter();
  return (
    <div className="about-page">
      <div className="modal about-card">
        <p className="eyebrow">JMU CISE</p>
        <h2>About ISAT Recruiter</h2>
        <p>
          ISAT Recruiter is a chatbot that answers questions about the ISAT program.
          To explore the ISAT website, use the link below.
        </p>
        <a
          className="modal-link"
          href="https://www.jmu.edu/cise/isat/index.shtml"
          target="_blank"
          rel="noopener noreferrer"
        >
          Visit the ISAT website
        </a>
        <button type="button" className="text-button" onClick={() => router.push('/')}>
          Back to chat
        </button>
      </div>
    </div>
  );
}
