import curses
import curses.textpad
import docker
import os, subprocess

HEALTHY_STATUS = 'healthy'
STARTING_STATUS = 'starting'

class Screen(object):
    UP = -1
    DOWN = 1
    LEFT = -3
    RIGHT = 3

    def __init__(self):
        """ Initialize the screen window

        Attributes
            window: A full curses screen window

            width: The width of `window`
            height: The height of `window`

            max_lines: Maximum visible line count for `result_window`
            top: Available top line position for current page (used on scrolling)
            bottom: Available bottom line position for whole pages (as length of items)
            current: Current highlighted line number (as window cursor)
            page: Total page count which being changed corresponding to result of a query (starts from 0)

            ┌--------------------------------------┐
            |1. Item                               |
            |--------------------------------------| <- top = 1
            |2. Item                               | 
            |3. Item                               |
            |4./Item///////////////////////////////| <- current = 3
            |5. Item                               |
            |6. Item                               |
            |7. Item                               |
            |8. Item                               | <- max_lines = 7
            |--------------------------------------|
            |9. Item                               |
            |10. Item                              | <- bottom = 10
            |                                      |
            |                                      | <- page = 1 (0 and 1)
            └--------------------------------------┘

        Returns
            None
        """
        self.window = None

        self.width = 0
        self.height = 0

        self.init_curses()

        self.containers = []

        self.max_lines = curses.LINES
        self.top = 0
        self.bottom = len(self.containers)
        self.current = 0
        self.page = self.bottom // self.max_lines
        self.action = ""
        self.client = docker.from_env()

    def init_curses(self):
        """Setup the curses"""
        self.window = curses.initscr()
        self.window.keypad(True)

        curses.noecho()
        curses.cbreak()
        curses.halfdelay(2)

        curses.start_color()
        curses.init_pair(1,
                        curses.COLOR_WHITE,
                        curses.COLOR_RED)
        curses.init_pair(2,
                        curses.COLOR_WHITE,
                        curses.COLOR_GREEN)
        curses.init_pair(3,
                        curses.COLOR_WHITE,
                        curses.COLOR_YELLOW)
        curses.init_pair(4,
                        curses.COLOR_WHITE,
                        curses.COLOR_BLACK)
        curses.init_pair(5,
                        curses.COLOR_RED,
                        curses.COLOR_BLACK)
        curses.init_pair(6,
                        curses.COLOR_GREEN,
                        curses.COLOR_BLACK)
        curses.init_pair(7,
                        curses.COLOR_BLACK,
                        curses.COLOR_WHITE)
        curses.init_pair(8,
                        curses.COLOR_YELLOW,
                        curses.COLOR_BLACK)

        self.current = curses.color_pair(2)

        self.height, self.width = self.window.getmaxyx()

    def run(self):
        """Continue running the TUI until get interrupted"""
        try:
            self.input_stream()
        except KeyboardInterrupt:
            pass
        finally:
            curses.endwin()

    def input_stream(self):
        """Waiting an input and run a proper method according to type of input"""

        while True:
            self.containers = self.client.containers.list()
            self.bottom = len(self.containers)
            self.page = self.bottom // self.max_lines

            self.display()

            ch = self.window.getch()
            if ch == curses.KEY_UP:
                self.scroll(self.UP)
            elif ch == curses.KEY_DOWN:
                self.scroll(self.DOWN)
            elif ch == curses.KEY_LEFT:
                self.scroll(self.LEFT)
            elif ch == curses.KEY_RIGHT:
                self.scroll(self.RIGHT)
            elif ch in [10, 13, curses.KEY_ENTER]:
                self.doAction()
            elif ch == curses.ascii.ESC:
                break

    def doAction(self):
        for idx, container in enumerate(self.containers):
            if idx == self.current:
                self.action = container.name
                #os.system("docker restart " + container.name + " &")
                subprocess.Popen(["docker","restart",container.name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return

    def scroll(self, direction):
        """Scrolling the window when pressing up/down arrow keys"""
        # next cursor position after scrolling
        next_line = self.current + direction

        # Up direction scroll overflow
        # current cursor position is 0, but top position is greater than 0
        if (direction == self.UP) and (self.top > 0 and self.current == 0):
            self.top += direction
            return
        # Scroll up
        # current cursor position or top position is greater than 0
        if (direction == self.UP) and (self.top > 0 or self.current > 0):
            self.current = next_line
            return

        # Down direction scroll overflow
        # next cursor position touch the max lines, but absolute position of max lines could not touch the bottom
        if (direction == self.DOWN) and (next_line == self.max_lines) and (self.top + self.max_lines < self.bottom):
            self.top += direction
            return
        # Scroll down
        # next cursor position is above max lines, and absolute position of next cursor could not touch the bottom
        if (direction == self.DOWN) and (next_line < self.max_lines) and (self.top + next_line < self.bottom):
            self.current = next_line
            return

        # Scroll RIGHT
        # next cursor position is above max lines, and absolute position of next cursor could not touch the bottom
        if (direction == self.RIGHT) and (next_line < self.max_lines) and (self.top + next_line < self.bottom):
            self.current = next_line
            return

        # Scroll LEFT
        # next cursor position is above max lines, and absolute position of next cursor could not touch the bottom
        if (direction == self.LEFT) and (self.current >= 3):
            self.current = next_line
            return



    def paging(self, direction):
        """Paging the window when pressing left/right arrow keys"""
        current_page = (self.top + self.current) // self.max_lines
        next_page = current_page + direction
        # The last page may have fewer items than max lines,
        # so we should adjust the current cursor position as maximum item count on last page
        if next_page == self.page:
            self.current = min(self.current, self.bottom % self.max_lines - 1)

        # Page up
        # if current page is not a first page, page up is possible
        # top position can not be negative, so if top position is going to be negative, we should set it as 0
        if (direction == self.UP) and (current_page > 0):
            self.top = max(0, self.top - self.max_lines)
            return
        # Page down
        # if current page is not a last page, page down is possible
        if (direction == self.DOWN) and (current_page < self.page):
            self.top += self.max_lines
            return

    def display(self):
        """Display the items on window"""
        self.window.erase()
        height, width = self.window.getmaxyx()
        i = 3
        j = 0
        down, restart, up = 0, 0 ,0
        self.window.addstr(0, 0, "{:^20s} ".format("Administration Docker Barbhack 2021"), curses.color_pair(4) | curses.A_BOLD)
        self.window.addstr(1, 0, "{:^20s} ".format("-----------------------------------"), curses.color_pair(4) | curses.A_BOLD)
   
        for idx, container in enumerate(self.containers):
            state = self.client.api.inspect_container(container.id)
            if 'Health' in state['State']:
                healthcheck = state['State']['Health']['Status']
                if healthcheck != HEALTHY_STATUS and healthcheck != STARTING_STATUS:
                    if idx == self.current:
                        self.window.addstr(i, j, " {:20s} ".format(container.name), curses.color_pair(7) | curses.A_BOLD)
                    else:
                        self.window.addstr(i, j, " {:20s} ".format(container.name), curses.color_pair(1) | curses.A_BOLD)
                    down = down + 1
                elif healthcheck == STARTING_STATUS:
                    if idx == self.current:
                        self.window.addstr(i, j, " {:20s} ".format(container.name), curses.color_pair(7) | curses.A_BOLD)
                    else:
                        self.window.addstr(i, j, " {:20s} ".format(container.name), curses.color_pair(3) | curses.A_BOLD)
                    restart = restart + 1
                else:
                    if idx == self.current:
                        self.window.addstr(i, j, " {:20s} ".format(container.name), curses.color_pair(7) | curses.A_BOLD)
                    else:
                        self.window.addstr(i, j, " {:20s} ".format(container.name), curses.color_pair(2) | curses.A_BOLD)
                    up = up + 1
                i = i + 1
                if i == 6:
                    j = j + 22
                    i = 3

        self.window.addstr(height-1, 0, "{} ".format(str(up) + " UP"), curses.color_pair(6) | curses.A_BOLD)
        self.window.addstr(height-1, 6, "{} ".format(str(restart) + " RESTART"), curses.color_pair(8) | curses.A_BOLD)
        self.window.addstr(height-1, 17, "{} ".format(str(down) + " DOWN | "), curses.color_pair(5) | curses.A_BOLD)
        self.window.addstr(height-1, 26, "{} ".format("STATUS:"), curses.color_pair(4) | curses.A_BOLD)
        if self.action:
            self.window.addstr(height-1, 34, "{} ".format("LAST MANUAL ACTION: RESTART INITIATED ON CONTAINER " + self.action), curses.color_pair(4) | curses.A_BOLD)
        self.window.refresh()


def main():
    screen = Screen()
    screen.run()


if __name__ == '__main__':
    main()
