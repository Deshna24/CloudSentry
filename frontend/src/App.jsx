import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './auth';
import Layout from './components/Layout';
import { Spinner } from './components/ui';
import AttackLab from './pages/AttackLab';
import AuditLogs from './pages/AuditLogs';
import Dashboard from './pages/Dashboard';
import Instances from './pages/Instances';
import Login from './pages/Login';
import SecurityRules from './pages/SecurityRules';
import ThreatDetail from './pages/ThreatDetail';
import Threats from './pages/Threats';
import Traffic from './pages/Traffic';

function Protected({ children }) {
  const { user, ready } = useAuth();
  if (!ready) return <Spinner label="Starting CloudSentry" />;
  return user ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<Protected><Layout /></Protected>}>
        <Route index element={<Dashboard />} />
        <Route path="attack-lab" element={<AttackLab />} />
        <Route path="threats" element={<Threats />} />
        <Route path="threats/:id" element={<ThreatDetail />} />
        <Route path="traffic" element={<Traffic />} />
        <Route path="instances" element={<Instances />} />
        <Route path="rules" element={<SecurityRules />} />
        <Route path="audit" element={<AuditLogs />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
