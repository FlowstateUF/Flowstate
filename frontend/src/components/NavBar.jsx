import { useNavigate } from "react-router-dom";
import { Button, Group, Menu, Avatar } from "@mantine/core";
import {
  IconHome2,
  IconBooks,
  IconLayoutDashboard,
  IconInfoCircle,
  IconLogin,
  IconUser,
  IconSettings,
  IconLogout,
  IconHistory,
} from "@tabler/icons-react";
import brain from "../assets/generic_brain.png";
import classes from "./NavBar.module.css";

export default function NavBar({ isAuthed = true }) {
  const navigate = useNavigate();

  const handleLogout = () => {

    navigate("/login");
  };

  return (
    <header className={classes.header}>
      <div className={classes.inner}>

        {/* LEFT */}
        <button className={classes.brand} type="button" onClick={() => navigate("/courses")}>
          <img src={brain} alt="Flowstate" className={classes.logo} />
          <span className={classes.brandText}>Flowstate</span>
        </button>

        {/* CENTER */}
        <Group gap="sm" className={classes.nav}>
          <Button variant="subtle" leftSection={<IconBooks size={18} />} onClick={() => navigate("/courses")}>
            Courses
          </Button>

          <Button variant="subtle" leftSection={<IconLayoutDashboard size={18} />} onClick={() => navigate("/dashboard")}>
            Dashboard
          </Button>

          <Button variant="subtle" leftSection={<IconInfoCircle size={18} />} onClick={() => navigate("/about")}>
            About
          </Button>

          <Button variant="subtle" leftSection={<IconHistory size={18} />} onClick={() => navigate("/history")}
          >
            History
          </Button>
        </Group>

        {}
        <Group gap="sm" className={classes.actions}>
          {!isAuthed ? (
            <Button
              variant="light"
              leftSection={<IconLogin size={18} />}
              onClick={() => navigate("/login")}
            >
              Log in
            </Button>
          ) : (
            <Menu
                shadow="md"
                width={200}
                position="bottom"
                withArrow
                arrowPosition="center"
                offset={8}
            >
                <Menu.Target>
                    <Button variant="subtle" radius="xl" className={classes.accountBtn}>
                    <Avatar size={28} radius="xl" />
                    </Button>
                </Menu.Target>

                <Menu.Dropdown>
                    <Menu.Item
                    leftSection={<IconUser size={16} />}
                    onClick={() => navigate("/account")}
                    >
                    Account
                    </Menu.Item>

                    <Menu.Item
                    leftSection={<IconSettings size={16} />}
                    onClick={() => navigate("/settings")}
                    >
                    Settings
                    </Menu.Item>

                    <Menu.Divider />

                    <Menu.Item
                    color="red"
                    leftSection={<IconLogout size={16} />}
                    onClick={handleLogout}
                    >
                    Logout
                    </Menu.Item>
                </Menu.Dropdown>
            </Menu>
          )}
        </Group>

      </div>
    </header>
  );
}