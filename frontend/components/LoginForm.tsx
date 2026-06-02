"use client";

import { useState } from "react";

import { login } from "@/lib/auth";

interface LoginFormProps {
  /** Called once a session token has been stored, to reveal the dashboard. */
  onAuthed: () => void;
}

export function LoginForm({ onAuthed }: LoginFormProps): React.JSX.Element {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(
    event: React.FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const ok = await login(username, password);
      if (ok) {
        onAuthed();
      } else {
        setError("Incorrect username or password.");
      }
    } catch {
      setError("Could not reach the server. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-screen">
      <form className="login-card" onSubmit={handleSubmit}>
        <div className="login-brand">
          <span className="brand-mark" aria-hidden>
            🛰
          </span>
          <span className="brand-text">
            <span className="brand-name">FleetGuard</span>
            <span className="brand-sub">Sign in to continue</span>
          </span>
        </div>

        <label className="login-field">
          <span>Username</span>
          <input
            type="text"
            name="username"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
        </label>

        <label className="login-field">
          <span>Password</span>
          <input
            type="password"
            name="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>

        {error !== null && (
          <p className="login-error" role="alert">
            {error}
          </p>
        )}

        <button type="submit" className="login-submit" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
