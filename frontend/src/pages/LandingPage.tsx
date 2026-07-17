import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Bell, 
  Terminal, 
  CheckCircle2, 
  Activity, 
  GitBranch, 
  MessageSquare, 
  Check, 
  Lock, 
  X,
  ShieldAlert,
  TrendingUp,
  Workflow
} from 'lucide-react';
import { useAuthStore } from '../store/authStore';

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setAuth);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'login' | 'register'>('login');
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const toggleModal = () => {
    setIsModalOpen(!isModalOpen);
    setError(null);
    setEmail('');
    setPassword('');
    setFirstName('');
    setLastName('');
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Please provide email and password.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      
      // 1. Submit Credentials to Login Endpoint
      const loginResp = await fetch(`${BASE_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!loginResp.ok) {
        const err = await loginResp.json().catch(() => ({}));
        throw new Error(err.detail || 'Incorrect email or password.');
      }

      const { access_token } = await loginResp.json();

      // 2. Fetch User Profile
      const meResp = await fetch(`${BASE_URL}/api/v1/auth/me`, {
        headers: { 'Authorization': `Bearer ${access_token}` },
      });

      if (!meResp.ok) {
        throw new Error('Failed to retrieve user profile.');
      }

      const userProfile = await meResp.json();

      // 3. Fetch Organizations list
      const orgsResp = await fetch(`${BASE_URL}/api/v1/organizations/`, {
        headers: { 'Authorization': `Bearer ${access_token}` },
      });

      if (!orgsResp.ok) {
        throw new Error('Failed to retrieve tenant organization context.');
      }

      const orgs = await orgsResp.json();

      if (orgs.length === 0) {
        throw new Error('You do not belong to any tenant organization.');
      }

      // 4. Save to global state and redirect
      setAuth(access_token, userProfile, orgs[0].id);
      setIsModalOpen(false);
      navigate('/dashboard');

    } catch (err: any) {
      setError(err.message || 'An error occurred during authentication.');
    } finally {
      setLoading(false);
    }
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password || !firstName) {
      setError('First name, email, and password are required.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

      // Register user
      const regResp = await fetch(`${BASE_URL}/api/v1/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          password,
          first_name: firstName,
          last_name: lastName
        }),
      });

      if (!regResp.ok) {
        const err = await regResp.json().catch(() => ({}));
        throw new Error(err.detail || 'Registration failed.');
      }

      // Switch to login tab and auto-populate
      setActiveTab('login');
      setError('Registration successful! Please sign in with your credentials.');
    } catch (err: any) {
      setError(err.message || 'An error occurred during registration.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-[#F7F9FB] text-[#1b1b1d] selection:bg-[#dae2fd] selection:text-[#131b2e] font-sans">
      {/* TopNavBar */}
      <header className="w-full top-0 sticky z-50 bg-[#fcf8fa] border-b border-[#c6c6cd]">
        <div className="flex justify-between items-center h-16 px-8 max-w-screen-2xl mx-auto">
          <div className="font-mono text-xs tracking-tighter text-on-surface flex items-center gap-2 uppercase font-bold">
            <span className="w-2.5 h-2.5 rounded-full bg-[#00714d] animate-pulse"></span>
            AGY
          </div>
          <nav className="hidden md:flex items-center gap-8">
            <a className="text-[#000000] font-bold border-b-2 border-[#000000] pb-1 text-sm" href="#">Solutions</a>
            <a className="text-[#45464d] hover:text-[#1b1b1d] transition-colors duration-200 text-sm" href="#">Docs</a>
            <a className="text-[#45464d] hover:text-[#1b1b1d] transition-colors duration-200 text-sm" href="#">Network</a>
            <a className="text-[#45464d] hover:text-[#1b1b1d] transition-colors duration-200 text-sm" href="#">Pricing</a>
          </nav>
          <div className="flex items-center gap-4">
            <button 
              onClick={() => { toggleModal(); setActiveTab('login'); }}
              className="px-4 py-2 text-xs font-semibold text-[#45464d] hover:text-[#1b1b1d] transition-all font-mono uppercase"
            >
              Sign In
            </button>
            <button 
              onClick={() => { toggleModal(); setActiveTab('register'); }}
              className="px-6 py-2 bg-[#000000] text-white text-xs font-bold hover:opacity-90 active:opacity-80 transition-all font-mono uppercase"
            >
              Start Free
            </button>
          </div>
        </div>
      </header>

      <main className="flex-grow">
        {/* Hero Section */}
        <section className="relative pt-24 pb-24 overflow-hidden border-b border-[#c6c6cd] bg-[radial-gradient(#C6C6CD_1px,transparent_1px)] [background-size:32px_32px]">
          <div className="max-w-screen-xl mx-auto px-8 text-center">
            <h1 className="text-6xl md:text-8xl font-display text-[#0F172A] leading-none mb-6 tracking-[-0.04em] font-semibold">
              Sigint
            </h1>
            <p className="font-mono text-xs text-[#45464d] tracking-[0.2em] mb-12 uppercase">
              Zero-Friction Incident Triage and AI Diagnostics
            </p>
            <div className="flex flex-col sm:flex-row justify-center gap-4 items-center">
              <button 
                onClick={() => { toggleModal(); setActiveTab('login'); }}
                className="px-8 py-4 bg-[#0F172A] text-white text-xs font-mono uppercase tracking-widest hover:bg-black transition-all flex items-center gap-2"
              >
                <Workflow className="w-4.5 h-4.5" />
                Connect Workspace
              </button>
              <button 
                onClick={() => { toggleModal(); setActiveTab('register'); }}
                className="px-8 py-4 border border-[#76777d] text-[#0F172A] text-xs font-mono uppercase tracking-widest hover:bg-[#eceef0] transition-all flex items-center gap-2"
              >
                <TrendingUp className="w-4.5 h-4.5" />
                Start Trial
              </button>
            </div>
          </div>
        </section>

        {/* Interactive Showcase */}
        <section className="max-w-screen-xl mx-auto px-8 -mt-12 mb-24 relative z-10">
          <div className="bg-white border border-[#c6c6cd] flex flex-col md:flex-row h-auto md:h-[520px] overflow-hidden rounded-lg shadow-sm">
            {/* Left: Incident Table */}
            <div className="w-full md:w-7/12 border-r border-[#c6c6cd] flex flex-col">
              <div className="p-4 bg-[#f2f4f6] border-b border-[#c6c6cd] flex justify-between items-center">
                <span className="font-mono text-xs uppercase tracking-widest text-[#45464d]">Active Incidents (4)</span>
                <Activity className="text-[#45464d] w-4.5 h-4.5 animate-pulse" />
              </div>
              <div className="flex-grow overflow-y-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-[#e6e8ea] border-b border-[#c6c6cd]">
                      <th className="p-3 font-mono text-[10px] text-[#45464d] uppercase font-bold">Severity</th>
                      <th className="p-3 font-mono text-[10px] text-[#45464d] uppercase font-bold">Identity</th>
                      <th className="p-3 font-mono text-[10px] text-[#45464d] uppercase font-bold">Status</th>
                    </tr>
                  </thead>
                  <tbody className="text-xs text-[#1b1b1d]">
                    <tr className="border-b border-[#c6c6cd] hover:bg-[#f2f4f6] transition-colors">
                      <td className="p-3">
                        <span className="px-2 py-0.5 bg-[#ffdad6] text-[#ba1a1a] font-mono text-[10px] uppercase font-bold rounded">Critical</span>
                      </td>
                      <td className="p-3">SIG-901: DB Connection Timeout</td>
                      <td className="p-3 font-mono text-[#45464d] italic">Triaging...</td>
                    </tr>
                    <tr className="border-b border-[#c6c6cd] hover:bg-[#f2f4f6] transition-colors">
                      <td className="p-3">
                        <span className="px-2 py-0.5 bg-amber-100 text-amber-700 font-mono text-[10px] uppercase font-bold rounded">High</span>
                      </td>
                      <td className="p-3">SIG-898: S3 Bucket Permissions</td>
                      <td className="p-3 font-mono text-[#45464d] italic">Investigating</td>
                    </tr>
                    <tr className="border-b border-[#c6c6cd] hover:bg-[#f2f4f6] transition-colors">
                      <td className="p-3">
                        <span className="px-2 py-0.5 bg-amber-100 text-amber-700 font-mono text-[10px] uppercase font-bold rounded">High</span>
                      </td>
                      <td className="p-3">SIG-892: API Latency Spike</td>
                      <td className="p-3 font-mono text-[#45464d] italic">Active</td>
                    </tr>
                    <tr className="border-b border-[#c6c6cd] hover:bg-[#f2f4f6] transition-colors">
                      <td className="p-3">
                        <span className="px-2 py-0.5 bg-sky-100 text-sky-700 font-mono text-[10px] uppercase font-bold rounded">Medium</span>
                      </td>
                      <td className="p-3">SIG-885: SSL Expiry Warning</td>
                      <td className="p-3 font-mono text-[#45464d] italic">Assigned</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
            {/* Right: Timeline */}
            <div className="w-full md:w-5/12 bg-white flex flex-col">
              <div className="p-4 bg-[#f2f4f6] border-b border-[#c6c6cd]">
                <span className="font-mono text-xs uppercase tracking-widest text-[#45464d]">Diagnostics Timeline</span>
              </div>
              <div className="p-4 flex-grow overflow-y-auto space-y-4">
                {/* Slack Alert */}
                <div className="flex gap-3 items-start">
                  <div className="w-8 h-8 bg-[#e6e8ea] border border-[#c6c6cd] flex items-center justify-center shrink-0 rounded">
                    <Bell className="w-4 h-4 text-[#45464d]" />
                  </div>
                  <div className="flex-grow">
                    <div className="font-mono text-[10px] text-[#45464d] uppercase">Slack Alert @ 14:02:11</div>
                    <div className="p-2 border border-[#c6c6cd] bg-[#F7F9FB] mt-1 text-xs rounded">
                      "Critical spike in error rates detected in us-east-1 production."
                    </div>
                  </div>
                </div>
                {/* GitHub Commit */}
                <div className="flex gap-3 items-start">
                  <div className="w-8 h-8 bg-[#e6e8ea] border border-[#c6c6cd] flex items-center justify-center shrink-0 rounded">
                    <Terminal className="w-4 h-4 text-[#45464d]" />
                  </div>
                  <div className="flex-grow">
                    <div className="font-mono text-[10px] text-[#45464d] uppercase">GitHub Commit @ 14:01:45</div>
                    <div className="p-2 border border-[#c6c6cd] bg-[#F7F9FB] mt-1 text-xs font-mono rounded">
                      feat: update pool settings to dynamic (commit: <span className="text-[#515f74]">a1b2c3d</span>)
                    </div>
                  </div>
                </div>
                {/* AI Diagnostic Report */}
                <div className="p-4 bg-[#131b2e] text-[#dae2fd] border border-[#0F172A] relative rounded">
                  <div className="absolute top-2 right-2">
                    <CheckCircle2 className="w-4.5 h-4.5 text-[#10b981]" />
                  </div>
                  <div className="font-mono text-[10px] uppercase text-[#7c839b] mb-2">AI Diagnostic Report</div>
                  <div className="space-y-2 text-xs">
                    <div className="flex gap-2 items-start">
                      <span className="text-[#10b981]">•</span>
                      <span>High correlation between SIG-901 and commit a1b2c3d (Pool Settings).</span>
                    </div>
                    <div className="flex gap-2 items-start">
                      <span className="text-[#10b981]">•</span>
                      <span>Database connections saturated (max 200/200).</span>
                    </div>
                    <div className="flex gap-2 items-start">
                      <span className="text-[#10b981]">•</span>
                      <span>Recommended action: Rollback "pool settings" change.</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Features Grid */}
        <section className="max-w-screen-xl mx-auto px-8 mb-24">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-6 bg-white border border-[#c6c6cd] rounded-lg hover:border-black transition-all group">
              <div className="mb-4">
                <Workflow className="w-8 h-8 text-[#45464d] group-hover:text-black transition-colors" />
              </div>
              <h3 className="text-lg font-bold mb-2">Auto-Ingestion</h3>
              <p className="text-xs text-[#45464d] leading-relaxed">
                Native webhook support for Slack, GitHub, PagerDuty, and Datadog. Connect your stack in under 60 seconds without complex agents.
              </p>
            </div>
            <div className="p-6 bg-white border border-[#c6c6cd] rounded-lg hover:border-black transition-all group">
              <div className="mb-4">
                <GitBranch className="w-8 h-8 text-[#45464d] group-hover:text-black transition-colors" />
              </div>
              <h3 className="text-lg font-bold mb-2">Timeline Correlation</h3>
              <p className="text-xs text-[#45464d] leading-relaxed">
                Sigint maps disparate events onto a unified temporal plane, automatically highlighting causal relationships others miss.
              </p>
            </div>
            <div className="p-6 bg-white border border-[#c6c6cd] rounded-lg hover:border-black transition-all group">
              <div className="mb-4">
                <MessageSquare className="w-8 h-8 text-[#45464d] group-hover:text-black transition-colors" />
              </div>
              <h3 className="text-lg font-bold mb-2">Diagnostic Summaries</h3>
              <p className="text-xs text-[#45464d] leading-relaxed">
                LLM-powered post-mortems that extract logic from noise. Get clear, actionable steps instead of raw log dumps.
              </p>
            </div>
          </div>
        </section>

        {/* Pricing Section */}
        <section className="max-w-screen-xl mx-auto px-8 mb-24 text-center">
          <h2 className="text-3xl text-[#0F172A] mb-8 font-semibold">Platform Licensing</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
            {/* Free Tier */}
            <div className="bg-white border border-[#c6c6cd] p-6 rounded-lg flex flex-col text-left">
              <div className="flex justify-between items-start mb-4">
                <h3 className="text-lg font-bold">Free Tier</h3>
                <div className="text-3xl font-bold text-[#0F172A]">$0<span className="text-xs text-[#45464d] font-normal">/mo</span></div>
              </div>
              <ul className="space-y-2 mb-6 flex-grow text-xs">
                <li className="flex items-center gap-2">
                  <Check className="text-[#10b981] w-4.5 h-4.5" />
                  3 Connected Integrations
                </li>
                <li className="flex items-center gap-2">
                  <Check className="text-[#10b981] w-4.5 h-4.5" />
                  Webhook Correlation
                </li>
                <li className="flex items-center gap-2">
                  <Check className="text-[#10b981] w-4.5 h-4.5" />
                  24h Log Retention
                </li>
              </ul>
              <button 
                onClick={() => { toggleModal(); setActiveTab('register'); }}
                className="w-full py-3 bg-[#0F172A] text-white text-xs font-mono uppercase tracking-widest hover:bg-black transition-all"
              >
                Get Started
              </button>
            </div>
            {/* Premium Tier */}
            <div className="bg-[#f2f4f6] border-2 border-dashed border-[#c6c6cd] p-6 rounded-lg flex flex-col text-left opacity-80">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-lg font-bold text-[#1b1b1d]">Premium</h3>
                  <span className="px-2 py-0.5 bg-[#e6e8ea] text-[#45464d] font-mono text-[9px] uppercase font-bold rounded">Coming Soon</span>
                </div>
                <div className="text-3xl font-bold text-[#0F172A]">—</div>
              </div>
              <ul className="space-y-2 mb-6 flex-grow text-xs text-[#45464d]">
                <li className="flex items-center gap-2">
                  <Lock className="w-4 h-4" />
                  Unlimited Integrations
                </li>
                <li className="flex items-center gap-2">
                  <Lock className="w-4 h-4" />
                  Advanced AI Forensics
                </li>
                <li className="flex items-center gap-2">
                  <Lock className="w-4 h-4" />
                  SSO &amp; Audit Logs
                </li>
              </ul>
              <button className="w-full py-3 border border-[#c6c6cd] text-[#45464d] text-xs font-mono uppercase tracking-widest cursor-not-allowed" disabled>Notify Me</button>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="w-full bg-[#eceef0] border-t border-[#c6c6cd]">
        <div className="flex flex-col md:flex-row justify-between items-center py-6 px-8 gap-4 w-full max-w-screen-2xl mx-auto text-[10px]">
          <div className="font-mono font-bold text-[#1b1b1d] uppercase tracking-widest">
            © 2026 SIGINT.AI — PRECISIVE INTELLIGENCE OPERATIONS
          </div>
          <div className="flex gap-6">
            <a className="font-mono uppercase tracking-widest text-[#45464d] hover:text-[#1b1b1d] underline transition-all" href="#">Privacy Policy</a>
            <a className="font-mono uppercase tracking-widest text-[#45464d] hover:text-[#1b1b1d] underline transition-all" href="#">Terms of Service</a>
            <a className="font-mono uppercase tracking-widest text-[#45464d] hover:text-[#1b1b1d] underline transition-all" href="#">Security Audit</a>
          </div>
        </div>
      </footer>

      {/* Login Modal Overlay */}
      {isModalOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-[#0F172A]/20 backdrop-blur-[2px]">
          <div className="bg-white border border-[#c6c6cd] w-full max-w-md p-8 relative rounded-lg shadow-lg">
            <button 
              onClick={toggleModal}
              className="absolute top-4 right-4 text-[#45464d] hover:text-[#1b1b1d] p-1 hover:bg-[#f2f4f6] rounded"
            >
              <X className="w-5 h-5" />
            </button>
            <h2 className="text-xl font-bold text-[#0F172A] mb-4">Welcome to Sigint.AI</h2>
            
            <div className="flex border-b border-[#c6c6cd] mb-6">
              <button 
                onClick={() => { setActiveTab('login'); setError(null); }}
                className={`px-4 py-2 font-mono uppercase text-xs border-b-2 font-bold ${activeTab === 'login' ? 'border-black text-black' : 'border-transparent text-[#45464d]'}`}
              >
                Sign In
              </button>
              <button 
                onClick={() => { setActiveTab('register'); setError(null); }}
                className={`px-4 py-2 font-mono uppercase text-xs border-b-2 font-bold ${activeTab === 'register' ? 'border-black text-black' : 'border-transparent text-[#45464d]'}`}
              >
                Register
              </button>
            </div>

            {error && (
              <div className={`p-3 text-xs mb-4 rounded flex items-start gap-2 ${error.includes('successful') ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
                <ShieldAlert className="w-4.5 h-4.5 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            {activeTab === 'login' ? (
              <form className="space-y-4" onSubmit={handleLoginSubmit}>
                <div>
                  <label className="block font-mono text-[9px] text-[#45464d] mb-1 uppercase tracking-widest font-bold">Work Email</label>
                  <input 
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full bg-[#F7F9FB] border border-[#c6c6cd] p-3 focus:border-black focus:outline-none text-xs rounded transition-all" 
                    placeholder="name@company.com" 
                    required
                  />
                </div>
                <div>
                  <label className="block font-mono text-[9px] text-[#45464d] mb-1 uppercase tracking-widest font-bold">Password</label>
                  <input 
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full bg-[#F7F9FB] border border-[#c6c6cd] p-3 focus:border-black focus:outline-none text-xs rounded transition-all" 
                    placeholder="••••••••" 
                    required
                  />
                </div>
                <button 
                  type="submit" 
                  disabled={loading}
                  className="w-full py-3 bg-[#0F172A] text-white font-mono text-xs uppercase tracking-widest hover:bg-black transition-all rounded font-bold disabled:opacity-50"
                >
                  {loading ? 'Authenticating...' : 'Continue'}
                </button>
              </form>
            ) : (
              <form className="space-y-4" onSubmit={handleRegisterSubmit}>
                <div className="flex gap-4">
                  <div className="w-1/2">
                    <label className="block font-mono text-[9px] text-[#45464d] mb-1 uppercase tracking-widest font-bold">First Name</label>
                    <input 
                      type="text"
                      value={firstName}
                      onChange={(e) => setFirstName(e.target.value)}
                      className="w-full bg-[#F7F9FB] border border-[#c6c6cd] p-3 focus:border-black focus:outline-none text-xs rounded transition-all" 
                      placeholder="Jane" 
                      required
                    />
                  </div>
                  <div className="w-1/2">
                    <label className="block font-mono text-[9px] text-[#45464d] mb-1 uppercase tracking-widest font-bold">Last Name</label>
                    <input 
                      type="text"
                      value={lastName}
                      onChange={(e) => setLastName(e.target.value)}
                      className="w-full bg-[#F7F9FB] border border-[#c6c6cd] p-3 focus:border-black focus:outline-none text-xs rounded transition-all" 
                      placeholder="Doe" 
                    />
                  </div>
                </div>
                <div>
                  <label className="block font-mono text-[9px] text-[#45464d] mb-1 uppercase tracking-widest font-bold">Work Email</label>
                  <input 
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full bg-[#F7F9FB] border border-[#c6c6cd] p-3 focus:border-black focus:outline-none text-xs rounded transition-all" 
                    placeholder="jane.doe@company.com" 
                    required
                  />
                </div>
                <div>
                  <label className="block font-mono text-[9px] text-[#45464d] mb-1 uppercase tracking-widest font-bold">Password</label>
                  <input 
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full bg-[#F7F9FB] border border-[#c6c6cd] p-3 focus:border-black focus:outline-none text-xs rounded transition-all" 
                    placeholder="••••••••" 
                    required
                  />
                </div>
                <button 
                  type="submit" 
                  disabled={loading}
                  className="w-full py-3 bg-[#0F172A] text-white font-mono text-xs uppercase tracking-widest hover:bg-black transition-all rounded font-bold disabled:opacity-50"
                >
                  {loading ? 'Creating Account...' : 'Register'}
                </button>
              </form>
            )}

            <div className="mt-6 text-center">
              <a className="font-mono text-[9px] text-[#45464d] hover:text-black uppercase tracking-widest" href="#">Forgot Password?</a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
