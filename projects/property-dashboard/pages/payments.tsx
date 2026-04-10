import Layout from '../components/Layout';
import data from '../data.json';

const fmt = (n, currency = 'GBP') => new Intl.NumberFormat('en-GB', { style: 'currency', currency, maximumFractionDigits: 0 }).format(n);

// Build a comprehensive payment schedule
const payments = data.properties.flatMap(p => {
  const items = [];
  if (p.monthlyRent > 0) {
    items.push({
      id: `${p.id}-rent`,
      property: p.address.split(',')[0],
      propertyId: p.id,
      type: 'Rental Income',
      description: `Monthly rent – ${p.tenant?.name || 'Tenant'}`,
      amount: p.monthlyRent,
      currency: p.type === 'HK' ? 'HKD' : 'GBP',
      dueDate: '2025-04-01',
      category: 'income',
    });
  }
  if (p.groundRent?.amount > 0) {
    items.push({
      id: `${p.id}-gr`,
      property: p.address.split(',')[0],
      propertyId: p.id,
      type: 'Ground Rent',
      description: p.groundRent.note || `Ground rent`,
      amount: p.groundRent.amount,
      currency: 'GBP',
      dueDate: p.groundRent.dueDate,
      category: 'expense',
    });
  }
  if (p.serviceCharge?.amount > 0) {
    items.push({
      id: `${p.id}-sc`,
      property: p.address.split(',')[0],
      propertyId: p.id,
      type: 'Service Charge',
      description: p.serviceCharge.note || 'Service charge',
      amount: p.serviceCharge.amount,
      currency: p.type === 'HK' ? 'HKD' : 'GBP',
      dueDate: p.serviceCharge.dueDate,
      category: 'expense',
    });
  }
  if (p.parking?.monthlyRent > 0) {
    items.push({
      id: `${p.id}-park`,
      property: p.address.split(',')[0],
      propertyId: p.id,
      type: 'Parking Income',
      description: `Parking ${p.parking.unit}`,
      amount: p.parking.monthlyRent,
      currency: 'HKD',
      dueDate: '2025-04-01',
      category: 'income',
    });
  }
  return items;
});

const accountantPayments = (data.accountantInvoices || []).map(i => ({
  id: i.id,
  property: 'Accountant',
  propertyId: 'ACC',
  type: i.type,
  description: i.note,
  amount: i.amount,
  currency: i.currency || 'HKD',
  dueDate: i.dueDate,
  category: 'expense',
}));

const allPayments = [...payments, ...accountantPayments].sort((a, b) => new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime());

const totalIncome = allPayments.filter(p => p.category === 'income').reduce((s, p) => s + (p.currency === 'HKD' ? p.amount / 8.2 : p.amount), 0);
const totalExpenses = allPayments.filter(p => p.category === 'expense').reduce((s, p) => s + (p.currency === 'HKD' ? p.amount / 8.2 : p.amount), 0);

export default function Payments() {
  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Payments</h1>
          <p className="text-slate-500 text-sm mt-1">Rental income and property expenses tracker</p>
        </div>

        {/* Summary */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5">
            <div className="text-xs font-semibold text-emerald-600 uppercase tracking-wide mb-1">Monthly Income</div>
            <div className="text-2xl font-bold text-emerald-800">£{Math.round(totalIncome).toLocaleString()}</div>
            <div className="text-xs text-emerald-600 mt-1">{allPayments.filter(p => p.category === 'income').length} income items</div>
          </div>
          <div className="bg-red-50 border border-red-200 rounded-xl p-5">
            <div className="text-xs font-semibold text-red-600 uppercase tracking-wide mb-1">Monthly Expenses</div>
            <div className="text-2xl font-bold text-red-800">£{Math.round(totalExpenses).toLocaleString()}</div>
            <div className="text-xs text-red-600 mt-1">{allPayments.filter(p => p.category === 'expense').length} expense items</div>
          </div>
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">
            <div className="text-xs font-semibold text-blue-600 uppercase tracking-wide mb-1">Net Cash Flow</div>
            <div className="text-2xl font-bold text-blue-800">£{Math.round(totalIncome - totalExpenses).toLocaleString()}</div>
            <div className="text-xs text-blue-600 mt-1">After property expenses</div>
          </div>
        </div>

        {/* All payments table */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
            <h2 className="font-semibold text-slate-800">All Payment Items</h2>
            <span className="text-xs text-slate-400">{allPayments.length} items</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  {['Property', 'Type', 'Description', 'Amount', 'Due Date', 'Status'].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {allPayments.map(p => (
                  <tr key={p.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-800 text-xs">{p.property}</div>
                      <div className="text-slate-400 text-xs">{p.propertyId}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                        p.category === 'income' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'
                      }`}>
                        {p.type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-600 text-xs max-w-xs truncate">{p.description}</td>
                    <td className="px-4 py-3 font-bold text-slate-700 text-xs whitespace-nowrap">
                      {p.currency === 'HKD' ? 'HK$' : '£'}{p.amount.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-slate-600 text-xs whitespace-nowrap">{p.dueDate}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${
                        p.dueDate && new Date(p.dueDate) < new Date() ? 'bg-red-100 text-red-700' :
                        p.dueDate && new Date(p.dueDate) < new Date(Date.now() + 30 * 86400000) ? 'bg-amber-100 text-amber-700' :
                        'bg-slate-100 text-slate-600'
                      }`}>
                        {p.dueDate && new Date(p.dueDate) < new Date() ? 'Overdue' :
                         p.dueDate && new Date(p.dueDate) < new Date(Date.now() + 30 * 86400000) ? 'Due Soon' : 'Scheduled'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </Layout>
  );
}
