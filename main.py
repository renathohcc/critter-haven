from critter_haven.core.app import App


def main() -> None:
    app = App()
    try:
        app.run()
    finally:
        app.quit()


if __name__ == "__main__":
    main()
