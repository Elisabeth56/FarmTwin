import { Link } from "react-router-dom";

export default function FarmSetup() {
  return (
    <main className="min-h-screen bg-stone-50 text-stone-800 px-6 py-12">
      <div className="max-w-2xl mx-auto space-y-6">
        <h1 className="text-3xl font-semibold text-emerald-900">Farm Setup</h1>
        <p className="text-stone-600">
          Placeholder — the setup form arrives on Day 4.
        </p>
        <Link to="/" className="text-emerald-700 hover:underline">
          ← Back to landing
        </Link>
      </div>
    </main>
  );
}
