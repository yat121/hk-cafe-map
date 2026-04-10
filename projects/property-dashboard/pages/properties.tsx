import Layout from '../components/Layout';
import data from '../data.json';

const fmt = (n, currency = 'GBP') => new Intl.NumberFormat('en-GB', { style: 'currency', currency, maximumFractionDigits: 0 }).format(n);

export default function Properties() {
  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Properties</h1>
            <p className="text-slate-500 text-sm mt-1">{data.properties.length} properties in portfolio</p>
          </div>
          <div className="flex gap-2">
            <button className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors">
              + Add Property
            </button>
          </div>
        </div>

        {/* Filter tabs */}
        <div className="flex gap-2">
          {['All', 'UK', 'HK'].map(t => (
            <button key={t} className={`px-4 py-1.5 text-sm rounded-full font-medium transition-colors ${
              t === 'All' ? 'bg-slate-900 text-white' : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}>
              {t}
            </button>
          ))}
        </div>

        {/* Properties grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {data.properties.map((p) => (
            <div key={p.id} className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden hover:shadow-md transition-shadow">
              {/* Card header */}
              <div className={`h-2 ${p.type === 'UK' ? 'bg-blue-500' : 'bg-red-500'}`} />
              <div className="p-5">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="text-xs font-semibold text-slate-400 uppercase tracking-wide">{p.id}</div>
                    <h3 className="font-semibold text-slate-900 mt-1 text-sm leading-snug">{p.address.split(',')[0]}</h3>
                    <div className="text-xs text-slate-400 mt-0.5">{p.type === 'UK' ? 'London, UK' : 'Hong Kong'}</div>
                  </div>
                  <span className={`text-xs font-semibold px-2 py-1 rounded-full ${
                    p.type === 'UK' ? 'bg-blue-100 text-blue-700' : 'bg-red-100 text-red-700'
                  }`}>{p.type}</span>
                </div>

                <div className="grid grid-cols-2 gap-3 mt-4">
                  <div className="bg-slate-50 rounded-lg p-3">
                    <div className="text-xs text-slate-400 mb-1">Monthly Rent</div>
                    <div className="text-sm font-bold text-slate-800">
                      {p.type === 'HK' ? fmt(p.monthlyRent, 'HKD') : fmt(p.monthlyRent, 'GBP')}
                    </div>
                  </div>
                  <div className="bg-slate-50 rounded-lg p-3">
                    <div className="text-xs text-slate-400 mb-1">Current Value</div>
                    <div className="text-sm font-bold text-slate-800">
                      {p.type === 'HK' ? fmt(p.currentValue, 'HKD') : fmt(p.currentValue, 'GBP')}
                    </div>
                  </div>
                  <div className="bg-slate-50 rounded-lg p-3">
                    <div className="text-xs text-slate-400 mb-1">Purchase Date</div>
                    <div className="text-sm font-semibold text-slate-700">{p.purchaseDate}</div>
                  </div>
                  <div className="bg-slate-50 rounded-lg p-3">
                    <div className="text-xs text-slate-400 mb-1">Tenant Status</div>
                    <div className={`text-sm font-semibold ${
                      p.tenant?.status === 'active' ? 'text-emerald-600' : 'text-amber-600'
                    }`}>
                      {p.tenant?.status === 'active' ? 'Active' : p.tenant?.status === 'renewing' ? 'Renewing' : p.tenant?.status}
                    </div>
                  </div>
                </div>

                {/* Financial obligations */}
                {(p.groundRent?.amount > 0 || p.serviceCharge?.amount > 0) && (
                  <div className="mt-4 pt-4 border-t border-slate-100 space-y-2">
                    {p.groundRent?.amount > 0 && (
                      <div className="flex justify-between text-xs">
                        <span className="text-slate-500">Ground Rent</span>
                        <span className="font-medium text-slate-700">{fmt(p.groundRent.amount, p.type === 'HK' ? 'HKD' : 'GBP')} due {p.groundRent.dueDate}</span>
                      </div>
                    )}
                    {p.serviceCharge?.amount > 0 && (
                      <div className="flex justify-between text-xs">
                        <span className="text-slate-500">Service Charge</span>
                        <span className="font-medium text-slate-700">{fmt(p.serviceCharge.amount, p.type === 'HK' ? 'HKD' : 'GBP')} due {p.serviceCharge.dueDate}</span>
                      </div>
                    )}
                  </div>
                )}

                <div className="mt-4 pt-3 border-t border-slate-100">
                  <div className="text-xs text-slate-400">
                    <span className="font-medium text-slate-500">Manager:</span> {p.manager}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Layout>
  );
}
