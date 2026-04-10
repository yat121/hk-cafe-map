import Layout from '../components/Layout';
import data from '../data.json';

const fmt = (n, currency = 'GBP') => new Intl.NumberFormat('en-GB', { style: 'currency', currency, maximumFractionDigits: 0 }).format(n);

export default function Tenants() {
  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Tenants</h1>
          <p className="text-slate-500 text-sm mt-1">{data.properties.filter(p => p.tenant?.name).length} tenants across portfolio</p>
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { label: 'Active', count: data.properties.filter(p => p.tenant?.status === 'active').length, color: 'bg-emerald-50 text-emerald-700', border: 'border-emerald-200' },
            { label: 'Renewing', count: data.properties.filter(p => p.tenant?.status === 'renewing').length, color: 'bg-amber-50 text-amber-700', border: 'border-amber-200' },
            { label: 'Total Rent (GBP)', count: '£' + data.properties.reduce((s, p) => s + (p.type === 'UK' ? p.monthlyRent : 0), 0).toLocaleString(), color: 'bg-blue-50 text-blue-700', border: 'border-blue-200' },
            { label: 'Avg Renewal Rent', count: '£' + Math.round(data.properties.filter(p => p.tenant?.renewalRent).reduce((s, p) => s + p.tenant.renewalRent, 0) / data.properties.filter(p => p.tenant?.renewalRent).length).toLocaleString(), color: 'bg-violet-50 text-violet-700', border: 'border-violet-200' },
          ].map(k => (
            <div key={k.label} className={`bg-white rounded-xl border ${k.border} p-4 shadow-sm`}>
              <div className="text-2xl font-bold text-slate-900">{k.count}</div>
              <div className={`text-xs font-medium mt-1 ${k.color.replace('bg-', 'text-').replace('-50', '-600')}`}>{k.label}</div>
            </div>
          ))}
        </div>

        {/* Tenant list */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100">
            <h2 className="font-semibold text-slate-800">All Tenants</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  {['Property', 'Tenant Name', 'Lease Start', 'Lease End', 'Monthly Rent', 'Renewal Rent', 'Status'].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.properties.map(p => p.tenant?.name && (
                  <tr key={p.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-800 text-xs">{p.address.split(',')[0]}</div>
                      <div className="text-slate-400 text-xs">{p.id}</div>
                    </td>
                    <td className="px-4 py-3 font-medium text-slate-700 text-xs whitespace-nowrap">{p.tenant.name}</td>
                    <td className="px-4 py-3 text-slate-600 text-xs whitespace-nowrap">{p.tenant.contractStart}</td>
                    <td className="px-4 py-3 text-slate-600 text-xs whitespace-nowrap">{p.tenant.contractEnd}</td>
                    <td className="px-4 py-3 font-semibold text-slate-700 text-xs whitespace-nowrap">
                      {p.type === 'HK' ? fmt(p.monthlyRent, 'HKD') : fmt(p.monthlyRent, 'GBP')}
                    </td>
                    <td className="px-4 py-3 font-semibold text-slate-700 text-xs whitespace-nowrap">
                      {p.tenant.renewalRent ? (p.type === 'HK' ? fmt(p.tenant.renewalRent, 'HKD') : fmt(p.tenant.renewalRent, 'GBP')) : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${
                        p.tenant.status === 'active' ? 'bg-emerald-100 text-emerald-700' :
                        p.tenant.status === 'renewing' ? 'bg-amber-100 text-amber-700' :
                        'bg-slate-100 text-slate-600'
                      }`}>
                        {p.tenant.status === 'active' ? 'Active' : p.tenant.status === 'renewing' ? 'Renewing' : p.tenant.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Upcoming renewals */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100">
            <h2 className="font-semibold text-slate-800">Lease Renewals</h2>
          </div>
          <div className="divide-y divide-slate-100">
            {data.properties.filter(p => p.tenant?.renewalDate).map(p => {
              const daysUntil = Math.ceil((new Date(p.tenant.renewalDate).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24));
              return (
                <div key={p.id} className="px-5 py-4 flex items-center gap-4">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-sm font-bold flex-shrink-0 ${
                    daysUntil < 60 ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'
                  }`}>
                    📋
                  </div>
                  <div className="flex-1">
                    <div className="font-medium text-slate-800 text-sm">{p.tenant.name}</div>
                    <div className="text-xs text-slate-400">{p.address.split(',')[0]}</div>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <div className="text-sm font-semibold text-slate-700">Renewal: {p.tenant.renewalDate}</div>
                    <div className={`text-xs ${daysUntil < 60 ? 'text-amber-600 font-medium' : 'text-slate-400'}`}>
                      {daysUntil > 0 ? `${daysUntil} days away` : 'Overdue'}
                    </div>
                  </div>
                  {p.tenant.renewalRent && (
                    <div className="text-right flex-shrink-0">
                      <div className="text-sm font-bold text-slate-800">
                        {p.type === 'HK' ? fmt(p.tenant.renewalRent, 'HKD') : fmt(p.tenant.renewalRent, 'GBP')}
                      </div>
                      <div className="text-xs text-slate-400">new rent</div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </Layout>
  );
}
