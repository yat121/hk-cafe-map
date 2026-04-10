import Layout from '../components/Layout';
import data from '../data.json';

const fmt = (n, currency = 'GBP') => new Intl.NumberFormat('en-GB', { style: 'currency', currency, maximumFractionDigits: 0 }).format(n);

const totalValue = data.properties.reduce((s, p) => s + (p.currentValue || 0), 0);
const ukValue = data.properties.filter(p => p.type === 'UK').reduce((s, p) => s + p.currentValue, 0);
const hkValue = data.properties.filter(p => p.type === 'HK').reduce((s, p) => s + p.currentValue, 0);
const totalRentGBP = data.properties.filter(p => p.type === 'UK').reduce((s, p) => s + p.monthlyRent, 0);
const totalRentHKD = data.properties.filter(p => p.type === 'HK').reduce((s, p) => s + p.monthlyRent, 0);
const totalAnnualRentGBP = totalRentGBP * 12;
const totalGroundRent = data.properties.reduce((s, p) => s + (p.groundRent?.amount || 0), 0);
const totalServiceCharge = data.properties.reduce((s, p) => s + (p.serviceCharge?.amount || 0), 0);

const grossYield = ((totalAnnualRentGBP + (totalRentHKD / 8.2) * 12) / totalValue * 100).toFixed(1);

export default function Reports() {
  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Reports</h1>
          <p className="text-slate-500 text-sm mt-1">Portfolio performance and financial summary</p>
        </div>

        {/* Key metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { label: 'Portfolio Value', value: fmt(totalValue), sub: 'Total assets' },
            { label: 'Annual Rent (GBP equiv.)', value: fmt(totalAnnualRentGBP + (totalRentHKD / 8.2) * 12), sub: 'Per year' },
            { label: 'Gross Yield', value: `${grossYield}%`, sub: 'On total value' },
            { label: 'Monthly Net', value: fmt(totalRentGBP + totalRentHKD / 8.2 - totalGroundRent - totalServiceCharge), sub: 'After fixed costs' },
          ].map(k => (
            <div key={k.label} className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
              <div className="text-xs text-slate-400 font-medium mb-2 uppercase tracking-wide">{k.label}</div>
              <div className="text-xl sm:text-2xl font-bold text-slate-900">{k.value}</div>
              <div className="text-xs text-slate-400 mt-1">{k.sub}</div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          {/* Regional breakdown */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-100">
              <h2 className="font-semibold text-slate-800">Regional Breakdown</h2>
            </div>
            <div className="p-5 space-y-4">
              {[
                {
                  region: '🇬🇧 United Kingdom',
                  currency: 'GBP',
                  props: data.properties.filter(p => p.type === 'UK'),
                  value: ukValue,
                  rent: totalRentGBP,
                },
                {
                  region: '🇭🇰 Hong Kong',
                  currency: 'HKD',
                  props: data.properties.filter(p => p.type === 'HK'),
                  value: hkValue,
                  rent: totalRentHKD,
                },
              ].map(r => (
                <div key={r.region}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-semibold text-slate-700">{r.region}</span>
                    <span className="text-xs text-slate-400">{r.props.length} propert{r.props.length !== 1 ? 'ies' : 'y'}</span>
                  </div>
                  <div className="space-y-2">
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-slate-500">Value</span>
                        <span className="font-semibold text-slate-700">
                          {r.currency === 'HKD' ? fmt(r.value, 'HKD') : fmt(r.value)}
                        </span>
                      </div>
                      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div className="h-full bg-blue-500 rounded-full" style={{ width: `${(r.value / totalValue * 100)}%` }} />
                      </div>
                      <div className="text-xs text-slate-400 mt-0.5">{r.value / totalValue * 100}% of portfolio</div>
                    </div>
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-slate-500">Monthly Rent</span>
                        <span className="font-semibold text-slate-700">
                          {r.currency === 'HKD' ? fmt(r.rent, 'HKD') : fmt(r.rent)}
                        </span>
                      </div>
                      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${(r.rent / (totalRentGBP + totalRentHKD / 8.2) * 100)}%` }} />
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Financial summary */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-100">
              <h2 className="font-semibold text-slate-800">Annual Financial Summary (GBP)</h2>
            </div>
            <div className="p-5 space-y-3">
              <div className="flex justify-between items-center py-2 border-b border-slate-50">
                <span className="text-sm text-slate-600">Rental Income (UK)</span>
                <span className="text-sm font-semibold text-emerald-600">+{fmt(totalAnnualRentGBP)}</span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-slate-50">
                <span className="text-sm text-slate-600">Rental Income (HK equiv.)</span>
                <span className="text-sm font-semibold text-emerald-600">+{fmt((totalRentHKD / 8.2) * 12)}</span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-slate-50">
                <span className="text-sm text-slate-600">Ground Rent Payable</span>
                <span className="text-sm font-semibold text-red-600">-{fmt(totalGroundRent * 12)}</span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-slate-50">
                <span className="text-sm text-slate-600">Service Charges</span>
                <span className="text-sm font-semibold text-red-600">-{fmt(totalServiceCharge * 12)}</span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-slate-50">
                <span className="text-sm text-slate-600">Accounting Fees (est.)</span>
                <span className="text-sm font-semibold text-red-600">-£2,000</span>
              </div>
              <div className="flex justify-between items-center py-3 bg-blue-50 rounded-lg px-3 mt-2">
                <span className="text-sm font-bold text-slate-800">Net Annual Income</span>
                <span className="text-sm font-bold text-blue-700">
                  {fmt(
                    totalAnnualRentGBP +
                    (totalRentHKD / 8.2) * 12 -
                    totalGroundRent * 12 -
                    totalServiceCharge * 12 -
                    2000
                  )}
                </span>
              </div>
              <div className="flex justify-between items-center py-2">
                <span className="text-xs text-slate-400">Net Monthly Average</span>
                <span className="text-xs font-bold text-slate-600">
                  {fmt((totalAnnualRentGBP + (totalRentHKD / 8.2) * 12 - totalGroundRent * 12 - totalServiceCharge * 12 - 2000) / 12)}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Property performance table */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100">
            <h2 className="font-semibold text-slate-800">Property Performance</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  {['Property', 'Value', 'Monthly Rent', 'Annual Rent', 'Yield', 'Ground Rent', 'Service Charge'].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.properties.map(p => {
                  const annualRent = (p.type === 'HK' ? p.monthlyRent / 8.2 : p.monthlyRent) * 12;
                  const propertyYield = ((annualRent / p.currentValue) * 100).toFixed(1);
                  return (
                    <tr key={p.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-4 py-3">
                        <div className="font-medium text-slate-800 text-xs">{p.address.split(',')[0]}</div>
                        <div className="text-slate-400 text-xs">{p.id}</div>
                      </td>
                      <td className="px-4 py-3 font-semibold text-slate-700 text-xs whitespace-nowrap">
                        {p.type === 'HK' ? fmt(p.currentValue, 'HKD') : fmt(p.currentValue)}
                      </td>
                      <td className="px-4 py-3 font-semibold text-slate-700 text-xs whitespace-nowrap">
                        {p.type === 'HK' ? fmt(p.monthlyRent, 'HKD') : fmt(p.monthlyRent)}
                      </td>
                      <td className="px-4 py-3 font-semibold text-emerald-700 text-xs whitespace-nowrap">
                        £{Math.round(annualRent).toLocaleString()}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-xs font-bold ${
                          parseFloat(propertyYield) > 4 ? 'text-emerald-600' : parseFloat(propertyYield) > 2 ? 'text-amber-600' : 'text-red-600'
                        }`}>
                          {propertyYield}%
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-600 text-xs whitespace-nowrap">
                        {p.type === 'HK' ? 'N/A' : `£${p.groundRent?.amount || 0}`}
                      </td>
                      <td className="px-4 py-3 text-slate-600 text-xs whitespace-nowrap">
                        {p.type === 'HK' ? fmt(p.serviceCharge?.amount || 0, 'HKD') : `£${p.serviceCharge?.amount || 0}`}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </Layout>
  );
}
