import { BrowserRouter, Route, Routes } from "react-router-dom";
import Landing from "./pages/Landing";
import FarmSetup from "./pages/FarmSetup";
import FarmDashboard from "./pages/FarmDashboard";
import ComponentGallery from "./pages/ComponentGallery";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/setup" element={<FarmSetup />} />
        <Route path="/farm/:id" element={<FarmDashboard />} />
        {import.meta.env.DEV && <Route path="/_components" element={<ComponentGallery />} />}
      </Routes>
    </BrowserRouter>
  );
}
