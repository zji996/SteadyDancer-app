import { Routes, Route } from "react-router-dom";
import { Layout } from "./components";
import {
  DashboardPage,
  ProjectsListPage,
  ProjectDetailPage,
  AssetsTab,
  ExperimentsTab,
  JobsTab,
} from "./pages";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="projects" element={<ProjectsListPage />} />
        <Route path="projects/:projectId" element={<ProjectDetailPage />}>
          <Route path="assets" element={<AssetsTab />} />
          <Route path="experiments" element={<ExperimentsTab />} />
          <Route path="jobs" element={<JobsTab />} />
        </Route>
      </Route>
    </Routes>
  );
}
