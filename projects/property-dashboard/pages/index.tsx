import Layout from '../components/Layout';
import data from '../data.json';

const fmt = (n, currency = 'GBP') => new Intl.NumberFormat('en-GB', { style: 'currency', currency, maximumFractionDigits: 0 }).format(n);

const totalValue = data.properties.reduce((s, p) => s + (p.currentValue || 0), 0);
const totalRent = data.properties.reduce((s, p) => s + (p.monthlyRent || 0), 0);
const ukProps = data.properties.filter(p => p.type === 'UK').length;
const hkProps = data.properties.filter(p => p.type === 'HK').length;
const activeTenants = data.properties.filter(p => p.tenant?.status === 'active').length;
const renewing = data.properties.filter(p => p.tenant?.status === 'renewing').length;

// upcoming deadlines
const allDeadlines = [
  ...data.properties.map(p => ({
    label: `Ground Rent – ${p.id}`,
    date: p.groundRent?.dueDate,
    amount: p.groundRent?.amount,
    type: 'Ground Rent',
    property: p.address.split(',')[0],
  })),
  ...data.properties.map(p => ({
    label: `Service Charge – ${p.id}`,
    date: p.serviceCharge?.dueDate,
    amount: p.serviceCharge?.amount,
    type: 'Service Charge',
    property: p.address.split(',')[0],
  })),
  ...(data.accountantInvoices || []).map(i => ({
    label: `${i.type} – ${i.client.split(' - ')[0]}`,
    date: i.dueDate,
    amount: i.amount,
    currency: i.currency,
    type: i.type,
    property: 'Accountant',
  })),
  ...data.properties.map(p => ({
    label: `Tenant Renewal – ${p.tenant?.name}`,
    date: p.tenant?.renewalDate,
    amount: null as number | null,
    currency: '',
    type: 'Tenant Renewal',
    property: p.address.split(',')[0],
  })),
].filter(d => d.date) as any[];

allDeadlines.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

const upcomingRenewals = data.properties.filter(p => p.tenant?.renewalDate);
const kpis = [
  {
    label: 'Total Portfolio Value',
    value: fmt(totalValue),
    icon: '🏦',
    color: 'bg-blue-50 text-blue-700',
    sub: `${data.properties.length} properties`,
  },
  {
    label: 'Monthly Rental Income',
    value: fmt(totalRent) + '/mo',
    icon: '💰',
    color: 'bg-emerald-50 text-emerald-700',
    sub: 'Across all properties',
  },
  {
    label: 'Active Tenants',
    value: String(activeTenants),
    icon: '👤',
    color: 'bg-violet-50 text-violet-700',
    sub: `${renewing} renewing`,
  },
  {
    label: 'Upcoming Deadlines',
    value: String(allDeadlines.length),
    icon: '📅',
    color: 'bg-amber-50 text-amber-700',
    sub: 'Next 90 days',
  },
];

export default function Dashboard() {
  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Portfolio Overview</h1>
          <p className="text-slate-500 text-sm mt-1">
            {new Date().toLocaleDateString('en-GB', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {kpis.map((k) => (
            <div key={k.label} className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-lg ${k.color}`}>
                  {k.icon}
                </div>
              </div>
              <div className="text-2xl font-bold text-slate-900">{k.value}</div>
              <div className="text-sm font-medium text-slate-700 mt-0.5">{k.label}</div>
              <div className="text-xs text-slate-400 mt-1">{k.sub}</div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          {/* Properties Summary */}
          <div className="xl:col-span-2 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
              <h2 className="font-semibold text-slate-800">Properties</h2>
              <span className="text-xs text-slate-400">{data.properties.length} total</span>
            </div>
            <div className="divide-y divide-slate-100">
              {data.properties.map((p) => (
                <div key={p.id} className="px-5 py-3 flex items-center gap-4 hover:bg-slate-50 transition-colors">
                  <div className={`w-9 h-9 rounded-lg flex items-center justify-center text-sm font-bold flex-shrink-0 ${
                    p.type === 'UK' ? 'bg-blue-100 text-blue-700' : 'bg-red-100 text-red-700'
                  }`}>
                    {p.type}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-slate-800 truncate">{p.address.split(',')[0]}</div>
                    <div className="text-xs text-slate-400">{p.type === 'UK' ? 'London, UK' : 'Hong Kong'}</div>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <div className="text-sm font-semibold text-slate-800">{fmt(p.monthlyRent)}<span className="text-xs font-normal text-slate-400">/mo</span></div>
                    <div className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                      p.tenant?.status === 'active' ? 'bg-emerald-100 text-emerald-700' :
                      p.tenant?.status === 'renewing' ? 'bg-amber-100 text-amber-700' :
                      'bg-slate-100 text-slate-600'
                    }`}>
                      {p.tenant?.status === 'active' ? 'Active' : p.tenant?.status === 'renewing' ? 'Renewing' : p.tenant?.status}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Upcoming Deadlines */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
              <h2 className="font-semibold text-slate-800">Upcoming Deadlines</h2>
              <span className="text-xs text-slate-400">Next 90 days</span>
            </div>
            <div className="divide-y divide-slate-100">
              {allDeadlines.length === 0 && (
                <div className="px-5 py-8 text-center text-sm text-slate-400">No upcoming deadlines</div>
              )}
              {allDeadlines.slice(0, 8).map((d, i) => {
                const date = new Date(d.date);
                const daysUntil = Math.ceil((date.getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24));
                const isUrgent = daysUntil <= 30 && daysUntil >= 0;
                const isPast = daysUntil < 0;
                return (
                  <div key={i} className="px-5 py-3">
                    <div className="flex items-start gap-3">
                      <div className={`w-8 h-8 rounded-lg flex flex-col items-center justify-center flex-shrink-0 text-xs font-bold ${
                        isPast ? 'bg-slate-100 text-slate-400' :
                        isUrgent ? 'bg-red-100 text-red-700' :
                        'bg-blue-100 text-blue-700'
                      }`}>
                        <div>{date.toLocaleString('default', { month: 'short' })}</div>
                        <div>{date.getDate()}</div>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">{d.type}</div>
                        <div className="text-sm text-slate-700 mt-0.5">{d.label}</div>
                        <div className="text-xs text-slate-400 mt-0.5">{d.property}</div>
                        {d.amount > 0 && (
                          <div className="text-xs font-medium text-slate-600 mt-0.5">{fmt(d.amount, d.currency || 'GBP')}{d.currency ? '' : ''}</div>
                        )}
                      </div>
                      {daysUntil >= 0 ? (
                        <span className={`text-xs font-medium flex-shrink-0 ${isUrgent ? 'text-red-600' : 'text-slate-400'}`}>
                          {daysUntil === 0 ? 'Today' : `${daysUntil}d`}
                        </span>
                      ) : (
                        <span className="text-xs text-slate-400 flex-shrink-0">{Math.abs(daysUntil)}d ago</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Portfolio Split */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <div className="text-sm text-slate-500 mb-3">Portfolio by Region</div>
            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-600">🇬🇧 UK ({ukProps} properties)</span>
                  <span className="font-semibold text-slate-700">{fmt(data.properties.filter(p => p.type === 'UK').reduce((s, p) => s + p.currentValue, 0))}</span>
                </div>
                <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-500 rounded-full" style={{ width: `${(data.properties.filter(p => p.type === 'UK').reduce((s, p) => s + p.currentValue, 0) / totalValue * 100)}%` }} />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-600">🇭🇰 HK ({hkProps} properties)</span>
                  <span className="font-semibold text-slate-700">{fmt(data.properties.filter(p => p.type === 'HK').reduce((s, p) => s + p.currentValue, 0))}</span>
                </div>
                <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div className="h-full bg-red-500 rounded-full" style={{ width: `${(data.properties.filter(p => p.type === 'HK').reduce((s, p) => s + p.currentValue, 0) / totalValue * 100)}%` }} />
                </div>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <div className="text-sm text-slate-500 mb-3">Monthly Income</div>
            <div className="text-3xl font-bold text-slate-900">{fmt(totalRent)}</div>
            <div className="text-xs text-emerald-600 mt-1">+£{fmt(totalRent * 12)} projected annually</div>
            <div className="mt-3 text-xs text-slate-400">
              {data.properties.filter(p => p.type === 'UK').reduce((s, p) => s + p.monthlyRent, 0)} GBP from UK, {fmt(data.properties.filter(p => p.type === 'HK').reduce((s, p) => s + p.monthlyRent * (1/8.2), 0))} GBP equiv. from HK
            </div>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <div className="text-sm text-slate-500 mb-3">Lease Renewals</div>
            <div className="text-3xl font-bold text-slate-900">{renewing}</div>
            <div className="text-xs text-amber-600 mt-1">⚠ {renewing} tenant{renewing !== 1 ? 's' : ''} renewing soon</div>
            <div className="mt-3 space-y-1">
              {upcomingRenewals.map(p => (
                <div key={p.id} className="text-xs text-slate-500">
                  {p.tenant?.name?.split('/')[0]} – due {p.tenant?.renewalDate}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
