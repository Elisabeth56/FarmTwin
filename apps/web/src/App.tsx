import { BrowserRouter, Route, Routes } from "react-router-dom";
import Farms from "./pages/Farms";
import FarmSetup from "./pages/FarmSetup";
import FarmDashboard from "./pages/FarmDashboard";
import ComponentGallery from "./pages/ComponentGallery";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Farms />} />
        <Route path="/setup" element={<FarmSetup />} />
        <Route path="/farm/:id" element={<FarmDashboard />} />
        {import.meta.env.DEV && <Route path="/_components" element={<ComponentGallery />} />}
      </Routes>
    </BrowserRouter>
  );
}
