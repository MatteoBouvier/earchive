pub(crate) trait Renderer {
    fn render(&self, count: usize, total: usize);
    fn terminate(&self, count: usize);
}

pub(crate) struct CLIRenderer {
    len: usize,
}

impl CLIRenderer {
    const CLEAR: &'static str = "\x1b[0G\x1b[0J";

    pub fn new(len: usize) -> Self {
        Self { len: len }
    }

    fn print(&self, msg: &str) {
        let clear = CLIRenderer::CLEAR;
        eprint!("{clear}");

        eprint!("{msg}");
    }
}

impl Renderer for CLIRenderer {
    fn render(&self, count: usize, total: usize) {
        match (count, total) {
            (0, 0) => {
                let text = " ??".repeat(self.len.div_ceil(3))[..self.len].to_string();
                self.print(&format!("[{text}] 0/0"));
            }
            (_, 0) => self.print(&format!("[{}] {}/0", " ".repeat(self.len), count)),
            (0, _) => self.print(&format!("[{}] 0/{}", " ".repeat(self.len), total)),
            _ => {
                let progress = count.div_ceil(total) * self.len;
                self.print(&format!(
                    "[{}{}] {}/{}",
                    "#".repeat(progress),
                    " ".repeat(self.len - progress),
                    count,
                    total
                ));
            }
        }
    }

    fn terminate(&self, count: usize) {
        self.print(&format!("Done (analyzed {} files)\n", count));
    }
}
