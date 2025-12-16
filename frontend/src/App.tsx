import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Transactions from './pages/Transactions';
import Budgets from './pages/Budgets';
import SavingsGoals from './pages/SavingsGoals';
import Accounts from './pages/Accounts';
import Categories from './pages/Categories';
import ImportData from './pages/ImportData';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <nav className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center">
                <span className="text-xl font-bold text-gray-900">💰 Money Manager</span>
              </div>
              <div className="flex space-x-4">
                <NavLink 
                  to="/" 
                  className={({ isActive }) => 
                    `px-3 py-2 rounded-md text-sm font-medium ${isActive ? 'bg-gray-100 text-gray-900' : 'text-gray-600 hover:bg-gray-50'}`
                  }
                >
                  Dashboard
                </NavLink>
                <NavLink 
                  to="/transactions" 
                  className={({ isActive }) => 
                    `px-3 py-2 rounded-md text-sm font-medium ${isActive ? 'bg-gray-100 text-gray-900' : 'text-gray-600 hover:bg-gray-50'}`
                  }
                >
                  Transactions
                </NavLink>
                <NavLink 
                  to="/budgets" 
                  className={({ isActive }) => 
                    `px-3 py-2 rounded-md text-sm font-medium ${isActive ? 'bg-gray-100 text-gray-900' : 'text-gray-600 hover:bg-gray-50'}`
                  }
                >
                  Budgets
                </NavLink>
                <NavLink 
                  to="/goals" 
                  className={({ isActive }) => 
                    `px-3 py-2 rounded-md text-sm font-medium ${isActive ? 'bg-gray-100 text-gray-900' : 'text-gray-600 hover:bg-gray-50'}`
                  }
                >
                  Savings Goals
                </NavLink>
                <NavLink 
                  to="/accounts" 
                  className={({ isActive }) => 
                    `px-3 py-2 rounded-md text-sm font-medium ${isActive ? 'bg-gray-100 text-gray-900' : 'text-gray-600 hover:bg-gray-50'}`
                  }
                >
                  Accounts
                </NavLink>
                <NavLink 
                  to="/categories" 
                  className={({ isActive }) => 
                    `px-3 py-2 rounded-md text-sm font-medium ${isActive ? 'bg-gray-100 text-gray-900' : 'text-gray-600 hover:bg-gray-50'}`
                  }
                >
                  Categories
                </NavLink>
                <NavLink 
                  to="/import" 
                  className={({ isActive }) => 
                    `px-3 py-2 rounded-md text-sm font-medium ${isActive ? 'bg-gray-100 text-gray-900' : 'text-gray-600 hover:bg-gray-50'}`
                  }
                >
                  Import
                </NavLink>
              </div>
            </div>
          </div>
        </nav>
        
        <main className="max-w-7xl mx-auto px-4 py-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/transactions" element={<Transactions />} />
            <Route path="/budgets" element={<Budgets />} />
            <Route path="/goals" element={<SavingsGoals />} />
            <Route path="/accounts" element={<Accounts />} />
            <Route path="/categories" element={<Categories />} />
            <Route path="/import" element={<ImportData />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
