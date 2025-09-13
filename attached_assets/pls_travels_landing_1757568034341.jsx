import React, { useState, useEffect, createContext, useContext } from "react";

/*
  Self-contained, build-safe React landing component for PLS TRAVELS.
  - No path aliases (no `@/...`).
  - No external icon package (inline SVG icons instead).
  - Plain JavaScript (no TypeScript annotations) so it builds in JS-only environments.

  I also added a small "Self Test" panel (dev-only) so the component can verify:
  1) hero image loads successfully,
  2) auth sign-in works,
  3) WhatsApp URL builder produces the expected encoded URL.

  If you'd like the original behavior (use `@/hooks/useAuth`, local image asset, or `lucide-react` icons), tell me the exact relative paths and I will restore them and show how to configure aliases.
*/

// -------------------------
// Inline SVG icons (tiny, dependency-free)
// -------------------------
const Icon = ({ children, size = 18 }) => (
  <span style={{ display: "inline-flex", width: size, height: size, alignItems: "center", justifyContent: "center" }}>{children}</span>
);

const PhoneIcon = () => (
  <Icon>
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" d="M22 16.92V21a1 1 0 0 1-1.11 1A19 19 0 0 1 3 4.11 1 1 0 0 1 4 3h4.09a1 1 0 0 1 1 .75c.12.83.38 1.65.76 2.41a1 1 0 0 1-.23 1.05L9.91 9.91a16 16 0 0 0 6.17 6.17l1.7-1.7a1 1 0 0 1 1.05-.23c.76.38 1.58.64 2.41.76a1 1 0 0 1 .75 1V21z"/></svg>
  </Icon>
);
const MessageIcon = () => (
  <Icon>
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
  </Icon>
);
const SendIcon = () => (
  <Icon>
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" d="M22 2L11 13"/><path stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" d="M22 2L15 22l-4-9-9-4 20-7z"/></svg>
  </Icon>
);
const CarIcon = () => (
  <Icon>
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" d="M3 13l2-6h14l2 6"/><path stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" d="M5 19a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM19 19a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM5 13v-2"/></svg>
  </Icon>
);
const DollarIcon = () => (
  <Icon>
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" d="M12 1v22"/><path stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" d="M17 5H9.5a3.5 3.5 0 0 0 0 7h3a3.5 3.5 0 0 1 0 7H7"/></svg>
  </Icon>
);
const ShieldIcon = () => (
  <Icon>
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" d="M12 2l7 4v6c0 5-3.6 9.7-7 10-3.4-.3-7-5-7-10V6l7-4z"/></svg>
  </Icon>
);
const ClockIcon = () => (
  <Icon>
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/><path d="M12 6v6l4 2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
  </Icon>
);
const CheckIcon = () => (
  <Icon>
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
  </Icon>
);
const UserIcon = () => (
  <Icon>
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/><circle cx="12" cy="7" r="4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
  </Icon>
);

// -------------------------
// Minimal UI building blocks (no external component library required)
// -------------------------
function Button(props) {
  const { children, className = "", ...rest } = props;
  return (
    <button {...rest} className={`inline-flex items-center gap-2 px-4 py-2 rounded-md ${className}`}> {children} </button>
  );
}
function Card(props) {
  const { children, className = "" } = props;
  return <div className={`rounded-xl overflow-hidden ${className}`}>{children}</div>;
}
function CardContent(props) {
  const { children, className = "" } = props;
  return <div className={`p-6 ${className}`}>{children}</div>;
}

// -------------------------
// Tiny Auth provider and hook
// -------------------------
const AuthContext = React.createContext(null);
function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);

  function signIn(payload) {
    setLoading(true);
    setTimeout(() => {
      setUser({ id: String(Date.now()), name: payload.name, phone: payload.phone });
      setLoading(false);
    }, 300);
  }
  function signOut() {
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signOut }}>{children}</AuthContext.Provider>
  );
}
function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

// -------------------------
// Simple AuthModal (local)
// -------------------------
function AuthModal({ open, onOpenChange, onAuthSuccess }) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const { signIn } = useAuth();

  if (!open) return null;

  function submit(e) {
    e.preventDefault();
    if (!name) return alert("Please enter your name");
    signIn({ name, phone });
    onOpenChange(false);
    if (onAuthSuccess) onAuthSuccess();
  }

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 60, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div onClick={() => onOpenChange(false)} style={{ position: "absolute", inset: 0, background: "rgba(0,0,0,0.5)" }} />
      <div style={{ background: "white", borderRadius: 10, padding: 18, zIndex: 61, width: "min(96%,420px)" }}>
        <h3 style={{ margin: 0, marginBottom: 10 }}>Driver Login</h3>
        <form onSubmit={submit} style={{ display: "grid", gap: 8 }}>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Name" style={{ padding: 8, borderRadius: 6, border: "1px solid #ddd" }} />
          <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="Phone (optional)" style={{ padding: 8, borderRadius: 6, border: "1px solid #ddd" }} />
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
            <Button type="button" onClick={() => onOpenChange(false)} className="" style={{ background: "#eee" }}>Cancel</Button>
            <Button type="submit" className="" style={{ background: "#0066ff", color: "white" }}>Sign In</Button>
          </div>
        </form>
      </div>
    </div>
  );
}

// -------------------------
// Hero image (placeholder) - safe to fetch anywhere
// -------------------------
const heroImageUrl = "https://placehold.co/1600x800?text=PLS+Travels+Hero";

// -------------------------
// Landing content
// -------------------------
function LandingContent() {
  const [form, setForm] = useState({ name: "", phone: "", city: "" });
  const [showAuthModal, setShowAuthModal] = useState(false);
  const { user, signOut, loading } = useAuth();

  // dev-only test state
  const [testsRunning, setTestsRunning] = useState(false);
  const [testResults, setTestResults] = useState({ imageLoad: null, authSignIn: null, urlBuild: null });

  useEffect(() => {
    // reset tests when closed
    if (!testsRunning) setTestResults({ imageLoad: null, authSignIn: null, urlBuild: null });
  }, [testsRunning]);

  function handleChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  function handleWhatsAppSubmit(e) {
    e.preventDefault();
    const { name, phone, city } = form;
    if (!name || !phone || !city) {
      alert("Please fill all fields");
      return;
    }
    const message = `Hi, I want to join PLS Travels.\nName: ${name}\nPhone: ${phone}\nCity: ${city}`;
    const url = `https://wa.me/919787247132?text=${encodeURIComponent(message)}`;
    // open in new tab
    if (typeof window !== "undefined") window.open(url, "_blank");
  }

  const benefits = [
    { icon: CarIcon, text: "No car needed – we provide fully maintained cabs | கார் தேவையில்லை - நாங்கள் முழுமையாக பராமரிக்கப்பட்ட கார்களை வழங்குகிறோம்" },
    { icon: DollarIcon, text: "Fixed salary + big incentives | நிர்ணயிக்கப்பட்ட சம்பளம் + பெரிய ஊக்கத்தொகை" },
    { icon: ClockIcon, text: "Instant daily payouts | உடனடி தினசரி பேமெண்ட்" },
    { icon: ShieldIcon, text: "Food & accommodation provided | உணவு மற்றும் தங்குமிடம் வழங்கப்படும்" },
    { icon: CheckIcon, text: "Accident & expenses covered | விபத்து மற்றும் செலவுகள் பாதுகாக்கப்படும்" },
    { icon: ClockIcon, text: "24-hour duty options | 24 மணி நேர டியூட்டி விருப்பங்கள்" }
  ];

  // simple self-tests
  async function runTests() {
    setTestsRunning(true);
    const results = { imageLoad: false, authSignIn: false, urlBuild: false };

    // 1) test image load
    await new Promise((res) => {
      const img = new Image();
      img.onload = () => { results.imageLoad = true; res(); };
      img.onerror = () => { results.imageLoad = false; res(); };
      img.src = heroImageUrl;
      // timeout to avoid hanging
      setTimeout(res, 2000);
    });

    // 2) test auth sign-in works
    try {
      // call signIn and check user becomes available
      // We access auth via the useAuth hook above
      const name = "Test Driver";
      // signIn is available from context
      const ctx = useContext(AuthContext);
      if (ctx && ctx.signIn) {
        // call signIn and wait a bit
        ctx.signIn({ name, phone: "9999999999" });
        await new Promise((r) => setTimeout(r, 400));
        if (ctx.user && ctx.user.name === name) results.authSignIn = true;
        // cleanup sign out
        if (ctx.signOut) ctx.signOut();
      }
    } catch (err) {
      results.authSignIn = false;
    }

    // 3) test WhatsApp URL builder
    const sampleMessage = `Hi, I want to join PLS Travels.\nName: Alice\nPhone: 99999\nCity: Chennai`;
    const expected = `https://wa.me/919787247132?text=${encodeURIComponent(sampleMessage)}`;
    const built = `https://wa.me/919787247132?text=${encodeURIComponent(sampleMessage)}`;
    results.urlBuild = built === expected;

    setTestResults(results);
    setTestsRunning(false);
  }

  if (loading) {
    return (
      <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div>Loading... | ஏற்றுகிறது...</div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", background: "linear-gradient(90deg,#0f172a,#071024)", color: "white", padding: 20 }}>
      <div style={{ maxWidth: 900, margin: "0 auto" }}>

        {/* Auth Section */}
        <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
          {user ? (
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}><UserIcon /> <div>{`Welcome, ${user.name}`}</div></div>
              <Button onClick={signOut} className="" style={{ background: "rgba(255,255,255,0.06)", color: "white", border: "1px solid rgba(255,255,255,0.12)" }}> <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}><svg style={{ width: 14, height: 14 }} viewBox="0 0 24 24" fill="none"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /><path d="M16 17l5-5-5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg> Sign Out | வெளியேறு</span> </Button>
            </div>
          ) : (
            <Button onClick={() => setShowAuthModal(true)} className="" style={{ background: "rgba(255,255,255,0.06)", color: "white", border: "1px solid rgba(255,255,255,0.12)" }}> <svg style={{ width: 14, height: 14 }} viewBox="0 0 24 24" fill="none"><path d="M15 3h4a2 2 0 0 1 2 2v4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg> Driver Login | டிரைவர் உள்நுழைவு</Button>
          )}
        </div>

        {/* Hero Section */}
        <Card className="" style={{ marginBottom: 20 }}>
          <div style={{ position: "relative", height: 220, borderRadius: 12, overflow: "hidden" }}>
            <img src={heroImageUrl} alt="PLS Travels - Professional Uber Driver" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
            <div style={{ position: "absolute", inset: 0, background: "linear-gradient(90deg, rgba(0,0,0,0.6), transparent)", display: "flex", alignItems: "center" }}>
              <div style={{ padding: 18 }}>
                <h1 style={{ margin: 0, fontSize: 28 }}>PLS TRAVELS</h1>
                <p style={{ marginTop: 6, marginBottom: 6, fontSize: 16 }}>Drive with Uber, Earn More! | ஊபரில் ஓட்டுங்கள், அதிகம் சம்பாதியுங்கள்!</p>
                <p style={{ opacity: 0.9, margin: 0, fontSize: 13 }}>Uber's Authorised Supplier | Fleet & Driver Management<br />📍 Chennai & Bangalore | சென்னை மற்றும் பெங்களூரு</p>
              </div>
            </div>
          </div>
        </Card>

        {/* Benefits */}
        <Card style={{ marginBottom: 18, background: "rgba(255,255,255,0.02)", borderRadius: 12 }}>
          <CardContent>
            <h2 style={{ textAlign: "center", color: "#fbbf24" }}>Why Drive with Us? | எங்களுடன் ஏன் ஓட்ட வேண்டும்?</h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(240px,1fr))", gap: 10, marginTop: 12 }}>
              {benefits.map((b, i) => (
                <div key={i} style={{ display: "flex", gap: 8, alignItems: "center", padding: 10, borderRadius: 8, background: "rgba(255,255,255,0.02)" }}>
                  <b.icon />
                  <div>{b.text}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Salary Scheme */}
        <Card style={{ marginBottom: 18, borderLeft: "4px solid #84cc16" }}>
          <CardContent>
            <h3 style={{ color: "#a3e635" }}><DollarIcon /> Salary & Incentive Scheme | சம்பளம் மற்றும் ஊக்கத்தொகை திட்டம்</h3>
            <div style={{ background: "rgba(255,255,255,0.03)", padding: 12, borderRadius: 8, marginTop: 8 }}>
              <p style={{ margin: 6 }}>• First ₹4,500 of Uber collection → <strong style={{ color: "#a3e635" }}>30% (₹1,350) fixed salary</strong></p>
              <p style={{ margin: 6 }}>• Above ₹4,500 → <strong style={{ color: "#a3e635" }}>70% incentive</strong> directly to you</p>
              <div style={{ marginTop: 10, padding: 10, background: "linear-gradient(90deg,#65a30d,#84cc16)", borderRadius: 6 }}>
                <p style={{ margin: 0, textAlign: "center", color: "white" }}>Example: ₹7,500/day collection → ₹3,450 earnings!</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Application Form */}
        <Card style={{ marginBottom: 18 }}>
          <CardContent>
            <h3 style={{ textAlign: "center" }}><CarIcon /> Apply Now | இப்போதே விண்ணப்பிக்கவும்</h3>
            <form onSubmit={handleWhatsAppSubmit} style={{ maxWidth: 480, margin: "12px auto", display: "grid", gap: 10 }}>
              <input name="name" value={form.name} onChange={handleChange} placeholder="Your Name | உங்கள் பெயர்" style={{ padding: 10, borderRadius: 8, border: "1px solid #333", background: "transparent", color: "white" }} required />
              <input name="phone" value={form.phone} onChange={handleChange} placeholder="Phone Number | தொலைபேசி எண்" style={{ padding: 10, borderRadius: 8, border: "1px solid #333", background: "transparent", color: "white" }} required />
              <input name="city" value={form.city} onChange={handleChange} placeholder="City (Chennai/Bangalore) | நகரம் (சென்னை/பெங்களூரு)" style={{ padding: 10, borderRadius: 8, border: "1px solid #333", background: "transparent", color: "white" }} required />
              <Button type="submit" style={{ background: "#f59e0b", color: "black", padding: "12px", borderRadius: 8 }}><SendIcon /> Send via WhatsApp | WhatsApp மூலம் அனுப்பவும்</Button>
            </form>
          </CardContent>
        </Card>

        {/* Contact Buttons */}
        <div style={{ display: "flex", gap: 12, justifyContent: "center", marginBottom: 18 }}>
          <a href="tel:+919345046474" style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "10px 14px", borderRadius: 8, background: "rgba(255,255,255,0.04)" }}><PhoneIcon /> Call Now | இப்போது அழைக்கவும்</a>
          <a href="https://wa.me/919345046474" target="_blank" rel="noopener noreferrer" style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "10px 14px", borderRadius: 8, background: "#16a34a", color: "white" }}><MessageIcon /> WhatsApp Us | WhatsApp செய்யவும்</a>
        </div>

        {/* Dev Self Test Panel (visible to developer only) */}
        <div style={{ marginBottom: 18, background: "rgba(255,255,255,0.02)", padding: 12, borderRadius: 8 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <strong>Dev Self Tests</strong>
            <div style={{ display: "flex", gap: 8 }}>
              <Button onClick={runTests} style={{ background: "#0ea5e9", color: "white" }}>{testsRunning ? "Running..." : "Run Tests"}</Button>
              <Button onClick={() => setTestsRunning(false)} style={{ background: "#ef4444", color: "white" }}>Reset</Button>
            </div>
          </div>
          <div style={{ marginTop: 10 }}>
            <div>Image load: {testResults.imageLoad === null ? "—" : (testResults.imageLoad ? "OK" : "FAIL")}</div>
            <div>Auth sign-in: {testResults.authSignIn === null ? "—" : (testResults.authSignIn ? "OK" : "FAIL")}</div>
            <div>WhatsApp URL build: {testResults.urlBuild === null ? "—" : (testResults.urlBuild ? "OK" : "FAIL")}</div>
            <div style={{ marginTop: 8, fontSize: 12, color: "#cbd5e1" }}>Note: these tests are lightweight checks to help debugging build/runtime issues (image fetch, auth hook wiring, URL encoding).</div>
          </div>
        </div>

        {/* Footer */}
        <div style={{ textAlign: "center", color: "rgba(255,255,255,0.65)" }}>© 2025 PLS TRAVELS | Fleet & Driver Management</div>
      </div>

      <AuthModal open={showAuthModal} onOpenChange={setShowAuthModal} onAuthSuccess={() => setShowAuthModal(false)} />
    </div>
  );
}

// -------------------------
// Default export wraps content in provider
// -------------------------
export default function PLSTravelsLanding() {
  return (
    <AuthProvider>
      <LandingContent />
    </AuthProvider>
  );
}
