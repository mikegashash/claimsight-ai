import React, { useMemo, useState } from "react";

type ScoreResp = {
  fraud_probability?: number;
  prob_label?: string;
  reasons?: string[];
  top_features?: string[];
  engine?: "rules" | "model";
};

const API_BASE =
  (import.meta as any).env?.VITE_API_BASE ||
  window.location.origin; // works with forwarded port

export default function FraudDashboard() {
  const [jsonText, setJsonText] = useState<string>(
    JSON.stringify(
      {
        claim_id: "C001",
        line_of_business: "Auto",
        late_report_days: 3,
        claim_amount: 12000,
        paid_to_date: 5000,
        reserve: 7000,
        claimant_age: 42,
        injury_severity: 2,
        police_report: true,
        prior_claims_count: 1,
      },
      null,
      2
    )
  );
  const [loading, setLoading] = useState(false);
  const [resp, setResp] = useState<ScoreResp | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [simpleMode, setSimpleMode] = useState(true);

  const endpoint = useMemo(
    () => `${API_BASE}/fraud/${simpleMode ? "score_simple" : "score"}`,
    [API_BASE, simpleMode]
  );

  async function onScore() {
    setError(null);
    setResp(null);
    setLoading(true);
    try {
      const payload = JSON.parse(jsonText);
      const r = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!r.ok) {
        setError(`${r.status} ${r.statusText}: ${await r.text()}`);
      } else {
        setResp(await r.json());
      }
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <h1 className="text-2xl font-semibold">Fraud Scoring</h1>

      <div className="flex items-center gap-3">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={simpleMode}
            onChange={(e) => setSimpleMode(e.target.checked)}
          />
          Use friendly endpoint (<code>/fraud/score_simple</code>)
        </label>
        <a
          className="text-blue-600 underline"
          href={`${API_BASE}/docs`}
          target="_blank"
        >
          API Docs
        </a>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="space-y-2">
          <div className="text-sm text-gray-600">
            Paste/Edit claim JSON ({simpleMode ? "minimal" : "strict"}):
          </div>
          <textarea
            value={jsonText}
            onChange={(e) => setJsonText(e.target.value)}
            className="w-full h-80 font-mono text-sm border rounded p-3"
          />
          <button
            onClick={onScore}
            disabled={loading}
            className="px-4 py-2 rounded bg-black text-white disabled:opacity-50"
          >
            {loading ? "Scoring…" : "Score Claim"}
          </button>
          {error && (
            <pre className="mt-3 p-3 bg-red-50 border text-red-700 text-sm whitespace-pre-wrap">
              {error}
            </pre>
          )}
        </div>

        <div className="space-y-3">
          <div className="text-sm text-gray-600">Result:</div>
          <div className="border rounded p-3 min-h-20">
            {!resp && <div className="text-gray-400">No score yet.</div>}
            {resp && (
              <div className="space-y-3">
                <div className="text-sm">
                  <b>Engine</b>: {resp.engine || "rules"}
                </div>
                {"fraud_probability" in (resp as any) && (
                  <div className="text-sm">
                    <b>Fraud Probability</b>:{" "}
                    {(resp as any).fraud_probability?.toFixed?.(3)}
                  </div>
                )}
                {"prob_label" in (resp as any) && (
                  <div className="text-sm">
                    <b>Label</b>: {(resp as any).prob_label}
                  </div>
                )}
                {resp.top_features?.length ? (
                  <div>
                    <div className="text-sm font-medium mb-1">
                      Top Features:
                    </div>
                    <ul className="list-disc pl-5 text-sm">
                      {resp.top_features.map((t, i) => (
                        <li key={i}>{t}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {resp.reasons?.length ? (
                  <div>
                    <div className="text-sm font-medium mb-1">Reasons:</div>
                    <ul className="list-disc pl-5 text-sm">
                      {resp.reasons.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
            )}
          </div>

          {resp && (
            <details className="text-sm">
              <summary className="cursor-pointer">Raw JSON</summary>
              <pre className="mt-2 bg-gray-50 p-3 rounded overflow-auto">
                {JSON.stringify(resp, null, 2)}
              </pre>
            </details>
          )}
        </div>
      </div>
    </div>
  );
}
