import { useState } from 'react';
import EntryPage from './pages/entryPage';
import ReportPage from './pages/reportPage';

export default function App() {
  const [currentPage, setCurrentPage] = useState('entry');

  return (
    <div>
      {currentPage === 'entry' ? (
        <EntryPage onNavigate={setCurrentPage} />
      ) : (
        <ReportPage onNavigate={setCurrentPage} />
      )}
    </div>
  );
}