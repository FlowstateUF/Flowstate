import { useNavigate } from "react-router-dom";
import { Button, Group, Menu } from "@mantine/core";
import {
  IconBooks,
  IconLayoutDashboard,
  IconInfoCircle,
  IconLogin,
  IconUser,
  IconLogout,
  IconBookUpload,
} from "@tabler/icons-react";
import brain from "../assets/generic_brain.png";
import classes from "./NavBar.module.css";

export default function NavBar({ isAuthed = true }) {
  const navigate = useNavigate();
  const navItems = [
    { label: "Upload", icon: IconBookUpload, onClick: () => navigate("/upload") },
    { label: "Textbooks", icon: IconBooks, onClick: () => navigate("/textbooks") },
    { label: "Dashboard", icon: IconLayoutDashboard, onClick: () => navigate("/dashboard") },
    { label: "About", icon: IconInfoCircle, onClick: () => navigate("/about") },
  ];

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
    navigate("/login");
  };

  return (
    <header className={classes.header}>
      <div className={classes.inner}>

        {/* LEFT */}
        <button className={classes.brand} type="button" onClick={() => navigate("/upload")}>
          <img src={brain} alt="Flowstate" className={classes.logo} />
          <span className={classes.brandText}>Flowstate</span>
        </button>

        {/* CENTER */}
        <Group gap="sm" className={classes.nav}>
          {navItems.map((item) => {
            const Icon = item.icon;

            return (
              <button
                key={item.label}
                type="button"
                className={classes.navItem}
                onClick={item.onClick}
              >
                <Icon size={24} stroke={1.9} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </Group>

        <Group gap="sm" className={classes.actions}>
          {!isAuthed ? (
            <Button
              variant="light"
              leftSection={<IconLogin size={18} />}
              className={classes.loginBtn}
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
                    <button type="button" className={`${classes.navItem} ${classes.accountNavItem}`}>
                      <IconUser size={24} stroke={1.9} />
                      <span>Account</span>
                    </button>
                </Menu.Target>

                <Menu.Dropdown>
                    <Menu.Item
                    leftSection={<IconUser size={16} />}
                    onClick={() => navigate("/account")}
                    >
                    Account
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
