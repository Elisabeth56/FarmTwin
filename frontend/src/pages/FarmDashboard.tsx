import { Link, useParams } from "react-router-dom";

export default function FarmDashboard() {
  const { id } = useParams<{ id: string }>();

  return (
    <main className="min-h-screen bg-stone-50 text-stone-800 px-6 py-12">
      <div className="max-w-4xl mx-auto space-y-6">
        <h1 className="text-3xl font-semibold text-emerald-900">
          Farm Dashboard
        </h1>
        <p className="text-stone-600">
          Farm ID: <span className="font-mono text-stone-800">{id}</span>
        </p>
        <p className="text-stone-500 text-sm">
          Placeholder — the real dashboard arrives on Day 4.
        </p>
        <Link to="/" className="text-emerald-700 hover:underline">
          ← Back to landing
        </Link>
      </div>
    </main>
  );
}
