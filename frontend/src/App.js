import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import RoutePlanner from "@/components/RoutePlanner";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<RoutePlanner />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
