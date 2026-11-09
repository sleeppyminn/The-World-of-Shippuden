from game import Game

if __name__ == "__main__":
    try:
        Game().run()
    except (KeyboardInterrupt, EOFError):
        print("\n\n  Until next time, shinobi.\n")
