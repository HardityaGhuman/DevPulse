import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Mail, Loader2, Save, Eye, Send } from "lucide-react";
import api from "@/lib/api";

const DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];

export default function DigestSettings() {
  const [settings, setSettings] = useState({ digest_frequency: "daily", digest_day: "monday", tracked_repos: [] });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [sending, setSending] = useState(false);
  const [preview, setPreview] = useState(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    api.get("/api/digest/settings")
      .then((res) => setSettings(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setMessage("");
    try {
      await api.post("/api/digest/settings", settings);
      setMessage("Settings saved!");
      setTimeout(() => setMessage(""), 3000);
    } catch (e) {
      setMessage("Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const handlePreview = async () => {
    setPreviewing(true);
    setPreview(null);
    try {
      const res = await api.post("/api/digest/preview");
      setPreview(res.data);
    } catch (e) {
      setMessage("Failed to generate preview");
    } finally {
      setPreviewing(false);
    }
  };

  const handleSendNow = async () => {
    setSending(true);
    try {
      await api.post("/api/digest/send-now");
      setMessage("Digest sent to your email!");
      setTimeout(() => setMessage(""), 3000);
    } catch (e) {
      setMessage("Failed to send digest");
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-48 bg-surface rounded animate-pulse" />
        <div className="card p-6 h-48 animate-pulse" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
          <Mail className="w-6 h-6 text-accent" /> Digest Settings
        </h1>
        <p className="text-muted mt-1">Configure your automated GitHub activity digests</p>
      </motion.div>

      {/* Settings Card */}
      <motion.div className="card p-6 space-y-6" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
        {/* Frequency */}
        <div>
          <label className="text-sm text-muted block mb-2">Digest Frequency</label>
          <div className="flex gap-2">
            {["off", "daily", "weekly"].map((freq) => (
              <button
                key={freq}
                onClick={() => setSettings((s) => ({ ...s, digest_frequency: freq }))}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  settings.digest_frequency === freq
                    ? "bg-accent text-white"
                    : "bg-surface-alt text-muted hover:text-primary border border-border"
                }`}
              >
                {freq.charAt(0).toUpperCase() + freq.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Day (for weekly) */}
        {settings.digest_frequency === "weekly" && (
          <div>
            <label className="text-sm text-muted block mb-2">Digest Day</label>
            <select
              value={settings.digest_day}
              onChange={(e) => setSettings((s) => ({ ...s, digest_day: e.target.value }))}
              className="bg-surface-alt border border-border rounded-lg px-3 py-2 text-sm text-primary focus:border-accent outline-none"
            >
              {DAYS.map((d) => (
                <option key={d} value={d}>{d.charAt(0).toUpperCase() + d.slice(1)}</option>
              ))}
            </select>
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-wrap items-center gap-3 pt-4 border-t border-border">
          <button onClick={handleSave} disabled={saving} className="inline-flex items-center gap-2 bg-accent text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-accent/90 disabled:opacity-50 transition-colors">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Save Settings
          </button>
          <button onClick={handlePreview} disabled={previewing || settings.digest_frequency === "off"} className="inline-flex items-center gap-2 bg-surface-alt text-primary px-5 py-2 rounded-lg text-sm border border-border hover:border-accent disabled:opacity-50 transition-colors">
            {previewing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Eye className="w-4 h-4" />}
            Preview Digest
          </button>
          <button onClick={handleSendNow} disabled={sending || settings.digest_frequency === "off"} className="inline-flex items-center gap-2 bg-surface-alt text-primary px-5 py-2 rounded-lg text-sm border border-border hover:border-accent disabled:opacity-50 transition-colors">
            {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            Send Now
          </button>
          {message && <span className="text-sm text-success">{message}</span>}
        </div>
      </motion.div>

      {/* Preview */}
      {preview && (
        <motion.div className="card p-6 space-y-4" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
          <h2 className="text-lg font-semibold text-primary">Digest Preview</h2>
          <div className="bg-surface-alt rounded-lg p-4">
            <h3 className="text-accent font-semibold mb-2">{preview.digest?.headline}</h3>
            <div className="flex items-center gap-2 mb-4">
              <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                preview.digest?.momentum === "rising" ? "bg-success/10 text-success" :
                preview.digest?.momentum === "declining" ? "bg-destructive/10 text-destructive" :
                "bg-accent/10 text-accent"
              }`}>
                {preview.digest?.momentum?.toUpperCase()}
              </span>
              <span className="text-xs text-muted">Top repo: {preview.digest?.top_repo}</span>
            </div>
            {preview.digest?.highlights?.map((h, i) => (
              <p key={i} className="text-sm text-muted py-1">• {h}</p>
            ))}
            <div className="mt-4 pt-4 border-t border-border">
              <p className="text-sm text-muted"><span className="text-primary">🔥 Streak:</span> {preview.digest?.streak_comment}</p>
              <p className="text-sm text-muted mt-2"><span className="text-primary">💡 Tip:</span> {preview.digest?.coaching_tip}</p>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}
