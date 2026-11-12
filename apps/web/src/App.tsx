import { BrowserRouter, Route, Routes } from "react-router-dom";
import StartupGate from "./components/StartupGate";
import UpdateBanner from "./components/UpdateBanner";
import { ModelStatusProvider } from "./lib/model";
import Farms from "./pages/Farms";
import FarmSetup from "./pages/FarmSetup";
import FarmDashboard from "./pages/FarmDashboard";
import ComponentGallery from "./pages/ComponentGallery";
import ModelSetup from "./pages/ModelSetup";

export default function App() {
  return (
    <StartupGate>
    <ModelStatusProvider>
    <BrowserRouter>
      <UpdateBanner />
      <Routes>
        <Route path="/" element={<Farms />} />
        <Route path="/setup" element={<FarmSetup />} />
        <Route path="/farm/:id" element={<FarmDashboard />} />
        <Route path="/setup/model" element={<ModelSetup />} />
        {import.meta.env.DEV && <Route path="/_components" element={<ComponentGallery />} />}
      </Routes>
    </BrowserRouter>
    </ModelStatusProvider>
    </StartupGate>
  );
}
