import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Feed from "./pages/Feed";
import Login from "./pages/Login";
import Register from "./pages/Register";

function PrivateRoute({ children }) {
  return localStorage.getItem("access_token") ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route
          path="/"
          element={
            <PrivateRoute>
              <Feed />
            </PrivateRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
