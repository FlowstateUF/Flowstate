import NavBar from "../../components/NavBar";

export default function Dashboard() {
  return (
    <>
      <NavBar isAuthed={true} />
      <main style={{ padding: "40px" }}>
        <h1>Dashboard</h1>
      </main>
    </>
  );
}