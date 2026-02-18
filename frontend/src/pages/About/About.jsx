import NavBar from "../../components/NavBar";

export default function About() {
  return (
    <>
      <NavBar isAuthed={true} />
      <main style={{ padding: "40px" }}>
        <h1>About</h1>
      </main>
    </>
  );
}