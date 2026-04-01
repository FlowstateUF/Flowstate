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
            Flowstate was built by a group of five University of Florida students who all shared the same ideal: learning should be accessible, effective, and equitable for any student. While in college, every member of the Flowstate team experienced the obstacles that can come in the way when a student commits themselves to a higher education, whether that be dense course material, limited time, or just the pressure to keep up with the pace of ever expanding work. What stood out most to the team was how inaccessible tutoring or any type of academic support had become. The traditional tutoring services that were peppered around campus seemed designed to create a system where only affluent students could afford the help they needed, with services priced at hundreds of dollars a semester, it created an atmosphere where the average student felt alienated the second they walked through the door.
Frustrated by this reality, the team set out to build something different. In their senior year, Flowstate came together to create a platform that could bring that level of personailized academic support that one would buy from a professional institution, but without any financial barrier.
The mentality of Flowstate is to help students learn in a more direct and simplistic way, by cutting through the red tape and monotony that students find themselves getting lost in, it makes the entire learning experience less taxing and more engaging. Instead of relying on outdated study methods, students upload their own textbooks directly into the platform and Flowstate analyzes that content  in order to generate personalized learning experiences tailored to each individual’s strengths, weaknesses, and learning pace.
The goal of Flowstate isn’t just that students should pass exams, but it is to help students truly understand the material that they are learning. Through the reinforcement of comprehension and encouraging an active engagement with their study material, Flowstate allows students to build lasting confidence with their academic abilities.

          </p>
        </div>
      </main>
    </>
  );
}