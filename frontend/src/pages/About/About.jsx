import NavBar from "../../components/NavBar";
import "./About.css";

const PLACEHOLDER_IMG =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1200' height='800'%3E%3Cdefs%3E%3ClinearGradient id='g' x1='0' y1='0' x2='1' y2='1'%3E%3Cstop stop-color='%23e5e7eb'/%3E%3Cstop offset='1' stop-color='%23cbd5e1'/%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width='1200' height='800' fill='url(%23g)'/%3E%3Cpath d='M120 610 L420 340 L650 520 L820 380 L1080 610' fill='none' stroke='%2394a3b8' stroke-width='18' stroke-linecap='round' stroke-linejoin='round'/%3E%3Ccircle cx='470' cy='300' r='70' fill='%2394a3b8' opacity='0.45'/%3E%3Ctext x='50%25' y='52%25' dominant-baseline='middle' text-anchor='middle' font-family='Arial' font-size='44' fill='%2364748b'%3EFiller Image%3C/text%3E%3C/svg%3E";

export default function About() {
  return (
    <>
      <NavBar isAuthed={true} />

      {/* HERO */}
      <section className="about-hero">
        <div className="about-hero-inner">
          <h1 className="about-hero-title">About Flowstate</h1>

          <div className="about-hero-imageWrap">
            <img
              className="about-hero-image"
              src={PLACEHOLDER_IMG}
              alt="Students collaborating"
            />
          </div>
        </div>
      </section>

      {/* BODY */}
      <main className="about-body">
        <div className="about-body-inner">
          <p className="about-paragraph">
            Flowstate was created by a group of five dedicated University of Florida students with one simple goal:
              make learning more accessible to average student. For years this group was fed up with unnecessary and high-end tutoring fees
              that plauge university campuses, so they Flowstate was created as an alternative.
              The main mission behind flowstate was to to create a free, accessible way for students to improve their
            comprehension, practice smarter, and build real confidence with their classwork without
            paying hundreds of dollars just to keep up. Through Flowstate, students can upload their textbooks and recieve a personalized learning plan
              tailored to their strengths and weaknesses that ensures they can succeed in any classroom.Flowstate was created by a group of five dedicated University of Florida students with one simple goal:
              make learning more accessible to average student. For years this group was fed up with unnecessary and high-end tutoring fees
              that plauge university campuses, so they Flowstate was created as an alternative.
              The main mission behind flowstate was to to create a free, accessible way for students to improve their
            comprehension, practice smarter, and build real confidence with their classwork without
            paying hundreds of dollars just to keep up. Through Flowstate, students can upload their textbooks and recieve a personalized learning plan
              tailored to their strengths and weaknesses that ensures they can succeed in any classroom.

          </p>
        </div>
      </main>
    </>
  );
}