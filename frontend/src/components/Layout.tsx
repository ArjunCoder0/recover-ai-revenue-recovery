import React, { useState, useEffect } from 'react';
import {
  LayoutDashboard,
  FileSearch,
  Cpu,
  ShieldCheck,
  Server,
  UserCheck,
  History,
  FlaskConical,
  Layers,
  Map,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Menu,
  X,
} from 'lucide-react';
import { SimulationModal } from './SimulationModal';

export type NavPage =
  | 'overview'
  | 'cases'
  | 'decision'
  | 'policy'
  | 'reliability'
  | 'hitl'
  | 'audit'
  | 'experiment'
  | 'taxonomy'
  | 'mapping';

interface LayoutProps {
  children: React.ReactNode;
  activePage: NavPage;
  onNavigate: (page: NavPage) => void;
  simulationState: {
    n: number;
    seed: number;
    mock_mode: boolean;
  } | null;
  onRefreshSimulation: () => void;
}

export const Layout: React.FC<LayoutProps> = ({
  children,
  activePage,
  onNavigate,
  simulationState,
  onRefreshSimulation,
}) => {
  const [modalOpen, setModalOpen] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  // Close mobile drawer on resize to desktop
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 1024) {
        setMobileOpen(false);
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const navItems = [
    { id: 'overview' as NavPage, label: 'Overview', icon: LayoutDashboard, tag: 'KPIs' },
    { id: 'cases' as NavPage, label: 'Case Explorer', icon: FileSearch, tag: 'Why AI Chose' },
    { id: 'decision' as NavPage, label: 'Decision Intelligence', icon: Cpu, tag: 'Thompson AI' },
    { id: 'policy' as NavPage, label: 'Policy & Safety', icon: ShieldCheck, tag: 'R1–R8 Fence' },
    { id: 'reliability' as NavPage, label: 'Reliability & Gateway', icon: Server, tag: 'Idempotency' },
    { id: 'hitl' as NavPage, label: 'Human Review', icon: UserCheck, tag: 'HITL Queue' },
    { id: 'audit' as NavPage, label: 'Audit Trail', icon: History, tag: 'Tamper-Proof' },
    { id: 'experiment' as NavPage, label: 'Benchmark & Multi-Seed', icon: FlaskConical, tag: '10 Seeds' },
    { id: 'taxonomy' as NavPage, label: 'Failure Taxonomy', icon: Layers, tag: '4 Classes' },
    { id: 'mapping' as NavPage, label: 'Razorpay Integration Map', icon: Map, tag: 'Architecture' },
  ];

  const handleItemClick = (id: NavPage) => {
    onNavigate(id);
    setMobileOpen(false);
  };

  return (
    <div className="flex h-screen bg-[#F8FAFC] overflow-hidden text-slate-900 font-sans">
      
      {/* Mobile Backdrop Overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-40 lg:hidden transition-opacity duration-300"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Responsive Sidebar */}
      <aside
        className={`
          fixed inset-y-0 left-0 z-50 bg-white border-r border-slate-200/80 flex flex-col flex-shrink-0 transition-all duration-300 ease-in-out
          lg:static lg:z-20
          ${mobileOpen ? 'translate-x-0 shadow-2xl w-72' : '-translate-x-full lg:translate-x-0 shadow-none'}
          ${isCollapsed ? 'lg:w-[72px]' : 'lg:w-72'}
        `}
      >
        
        {/* Brand Area */}
        <div className={`p-4 border-b border-slate-100 flex items-center justify-between ${isCollapsed ? 'lg:justify-center' : ''}`}>
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-700 to-blue-500 flex items-center justify-center text-white font-black shadow-md shadow-blue-500/20 flex-shrink-0">
              ↺
            </div>
            
            {/* Brand text (hidden when collapsed on desktop) */}
            <div className={`transition-opacity duration-200 ${isCollapsed ? 'lg:hidden' : 'block'}`}>
              <div className="flex items-center gap-1.5">
                <span className="text-base font-extrabold tracking-tight text-slate-900">RECOVER</span>
                <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-blue-100/80 text-blue-700">
                  Track 3
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium truncate">Policy-Bounded AI Recovery</p>
            </div>
          </div>

          {/* Mobile Close Button */}
          <button
            onClick={() => setMobileOpen(false)}
            className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
            aria-label="Close sidebar"
          >
            <X className="w-5 h-5" />
          </button>

          {/* Desktop Collapse Toggle */}
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className={`hidden lg:flex p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors ${
              isCollapsed ? 'absolute -right-3 top-5 bg-white border border-slate-200 shadow-sm rounded-full p-1' : ''
            }`}
            title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? <ChevronRight className="w-3.5 h-3.5" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 overflow-y-auto px-2.5 py-4 space-y-1 scrollbar-thin">
          {!isCollapsed && (
            <p className="px-3 text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2 transition-opacity">
              Console Navigation
            </p>
          )}

          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activePage === item.id;
            return (
              <button
                key={item.id}
                onClick={() => handleItemClick(item.id)}
                title={isCollapsed ? item.label : undefined}
                className={`w-full flex items-center rounded-xl text-xs font-semibold transition-all group relative ${
                  isCollapsed ? 'lg:justify-center lg:px-0 py-2.5' : 'justify-between px-3 py-2.5'
                } ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-sm shadow-blue-600/25'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/80'
                }`}
              >
                <div className={`flex items-center gap-3 ${isCollapsed ? 'lg:gap-0' : ''}`}>
                  <Icon className={`w-4 h-4 flex-shrink-0 ${isActive ? 'text-white' : 'text-slate-400 group-hover:text-slate-600'}`} />
                  <span className={`truncate ${isCollapsed ? 'lg:hidden' : 'block'}`}>
                    {item.label}
                  </span>
                </div>

                {/* Tag Pill (hidden when collapsed) */}
                {item.tag && (
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded font-medium truncate ${
                      isCollapsed ? 'lg:hidden' : 'block'
                    } ${
                      isActive ? 'bg-blue-500/50 text-blue-50' : 'bg-slate-100 text-slate-500'
                    }`}
                  >
                    {item.tag}
                  </span>
                )}

                {/* Floating Tooltip when collapsed on desktop */}
                {isCollapsed && (
                  <div className="hidden lg:group-hover:flex absolute left-full ml-2 px-2.5 py-1 bg-slate-900 text-white text-[11px] font-medium rounded-lg shadow-lg whitespace-nowrap z-50 items-center gap-1.5 pointer-events-none animate-in fade-in-50 duration-150">
                    <span>{item.label}</span>
                    {item.tag && (
                      <span className="text-[9px] px-1 py-0.2 rounded bg-slate-800 text-blue-300">
                        {item.tag}
                      </span>
                    )}
                  </div>
                )}
              </button>
            );
          })}
        </nav>

        {/* Sidebar Footer */}
        <div className={`p-3.5 border-t border-slate-100 bg-slate-50/50 ${isCollapsed ? 'lg:p-2 lg:text-center' : ''}`}>
          <div className={`flex items-center gap-2 text-xs text-slate-600 ${isCollapsed ? 'lg:justify-center' : 'mb-1'}`}>
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse flex-shrink-0" />
            <span className={`font-semibold text-slate-800 truncate ${isCollapsed ? 'lg:hidden' : 'block'}`}>
              Mock Gateway Active
            </span>
          </div>
          <p className={`text-[11px] text-slate-400 leading-relaxed ${isCollapsed ? 'lg:hidden' : 'block'}`}>
            100% offline simulation. SQLite idempotency & policies active.
          </p>
        </div>

      </aside>

      {/* Main Content Viewport */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        
        {/* Top Header Bar */}
        <header className="h-16 bg-white border-b border-slate-200/80 px-4 sm:px-6 flex items-center justify-between flex-shrink-0 z-10">
          
          {/* Header Left: Hamburger Menu (mobile) & Mode indicators */}
          <div className="flex items-center gap-2 sm:gap-3">
            {/* Mobile menu trigger */}
            <button
              onClick={() => setMobileOpen(true)}
              className="lg:hidden p-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              aria-label="Open navigation menu"
            >
              <Menu className="w-5 h-5" />
            </button>

            {/* Mock Mode Badge */}
            <div className="flex items-center gap-1.5 sm:gap-2 px-2.5 sm:px-3 py-1 rounded-full bg-amber-50 border border-amber-200 text-amber-800 text-[11px] sm:text-xs font-semibold shadow-sm whitespace-nowrap">
              <span className="w-2 h-2 rounded-full bg-amber-500 flex-shrink-0" />
              <span>MOCK RAZORPAY MODE</span>
            </div>

            {/* Active batch info (hidden on mobile) */}
            <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-slate-100 border border-slate-200 text-slate-700 text-xs font-mono">
              <span>Batch: n={simulationState?.n || 400}</span>
              <span className="text-slate-300">|</span>
              <span>seed={simulationState?.seed || 42}</span>
            </div>
          </div>

          {/* Header Right: Run Simulation Trigger */}
          <div className="flex items-center gap-2 sm:gap-3">
            <button
              onClick={() => setModalOpen(true)}
              className="inline-flex items-center gap-1.5 sm:gap-2 px-3 sm:px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm transition-all whitespace-nowrap"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span className="hidden xs:inline sm:inline">Run Simulation</span>
              <span className="xs:hidden sm:hidden">Run</span>
            </button>
          </div>

        </header>

        {/* Content Body */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          <div className="max-w-7xl mx-auto space-y-6">
            {children}
          </div>
        </main>

        {/* Bottom Disclaimer */}
        <footer className="h-8 bg-white border-t border-slate-200/60 px-4 sm:px-6 flex items-center justify-between text-[11px] text-slate-400 flex-shrink-0">
          <span className="truncate">RECOVER · Razorpay Buildathon (Track 3: AI Revenue Recovery)</span>
          <span className="hidden sm:inline">Fully local execution · Safe offline simulation</span>
        </footer>

      </div>

      {/* Simulation Trigger Modal */}
      <SimulationModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        currentN={simulationState?.n || 400}
        currentSeed={simulationState?.seed || 42}
        onSuccess={onRefreshSimulation}
      />

    </div>
  );
};
