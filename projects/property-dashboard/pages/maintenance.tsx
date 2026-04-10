import Layout from '../components/Layout';

const maintenanceItems = [
  {
    id: 'm-1',
    property: 'Flat 1106, 8 Casson Square SE1 7GU',
    propertyId: 'uk-casson',
    issue: 'Annual building inspection required by JLL',
    category: 'Inspection',
    priority: 'medium',
    status: 'scheduled',
    date: '2025-09-01',
    cost: null,
  },
  {
    id: 'm-2',
    property: 'Flat 4203, Landmark Pinnacle',
    propertyId: 'uk-landmark',
    issue: 'Lease renewal & property inspection',
    category: 'Renewal',
    priority: 'high',
    status: 'scheduled',
    date: '2025-07-02',
    cost: null,
  },
  {
    id: 'm-3',
    property: 'Parking Bay 40, 101 Waterman House',
    propertyId: 'uk-waterman',
    issue: 'Annual ground rent demand review',
    category: 'Finance',
    priority: 'low',
    status: 'pending',
    date: '2025-12-01',
    cost: 50,
  },
  {
    id: 'm-4',
    property: '蝶翠峰12座1F, Hong Kong',
    propertyId: 'hk-diecuifeng',
    issue: 'Property management quarterly review',
    category: 'Management',
    priority: 'medium',
    status: 'scheduled',
    date: '2025-08-01',
    cost: null,
  },
  {
    id: 'm-5',
    property: 'Flat 1106, 8 Casson Square SE1 7GU',
    propertyId: 'uk-casson',
    issue: 'Service charge quarterly payment (Apr–Jun 2026)',
    category: 'Finance',
    priority: 'high',
    status: 'pending',
    date: '2025-07-01',
    cost: 350,
  },
];

const priorityColor = { high: 'bg-red-100 text-red-700', medium: 'bg-amber-100 text-amber-700', low: 'bg-blue-100 text-blue-700' };
const statusColor = { scheduled: 'bg-blue-100 text-blue-700', pending: 'bg-amber-100 text-amber-700', completed: 'bg-emerald-100 text-emerald-700' };

export default function Maintenance() {
  const totalCost = maintenanceItems.filter(m => m.cost).reduce((s, m) => s + m.cost, 0);

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Maintenance</h1>
            <p className="text-slate-500 text-sm mt-1">Property tasks, inspections and financial obligations</p>
          </div>
          <button className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors">
            + Add Task
          </button>
        </div>

        {/* Summary */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { label: 'Total Tasks', value: maintenanceItems.length, icon: '📋', bg: 'bg-slate-50' },
            { label: 'High Priority', value: maintenanceItems.filter(m => m.priority === 'high').length, icon: '🔴', bg: 'bg-red-50' },
            { label: 'Scheduled', value: maintenanceItems.filter(m => m.status === 'scheduled').length, icon: '📅', bg: 'bg-blue-50' },
            { label: 'Est. Cost', value: `£${totalCost}`, icon: '💷', bg: 'bg-emerald-50' },
          ].map(k => (
            <div key={k.label} className={`${k.bg} rounded-xl border border-slate-200 p-4`}>
              <div className="text-lg mb-1">{k.icon}</div>
              <div className="text-xl font-bold text-slate-900">{k.value}</div>
              <div className="text-xs text-slate-500 mt-0.5">{k.label}</div>
            </div>
          ))}
        </div>

        {/* Tasks list */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  {['Task', 'Property', 'Category', 'Priority', 'Due Date', 'Est. Cost', 'Status'].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {maintenanceItems.map(m => (
                  <tr key={m.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-slate-800 text-xs max-w-xs">{m.issue}</td>
                    <td className="px-4 py-3">
                      <div className="text-xs font-medium text-slate-700">{m.property.split(',')[0]}</div>
                      <div className="text-xs text-slate-400">{m.propertyId}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs font-medium px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full">{m.category}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${priorityColor[m.priority]}`}>
                        {m.priority.charAt(0).toUpperCase() + m.priority.slice(1)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-600 text-xs whitespace-nowrap">{m.date}</td>
                    <td className="px-4 py-3 font-semibold text-slate-700 text-xs whitespace-nowrap">
                      {m.cost ? `£${m.cost}` : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${statusColor[m.status]}`}>
                        {m.status.charAt(0).toUpperCase() + m.status.slice(1)}
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
