use crate::progress::render::Renderer;

pub struct ProgressBar {
    count: usize,
    total: usize,
    min_interval: f32,
    renderer: Box<dyn Renderer + Send + Sync>,
}

impl ProgressBar {
    pub fn new(renderer: Box<dyn Renderer + Send + Sync>) -> Self {
        Self {
            count: 0,
            total: 0,
            min_interval: 0.1,
            renderer,
        }
    }

    pub fn has_completed(&self) -> bool {
        self.count == self.total
    }

    pub fn update_count(&mut self) {
        self.count += 1;
        self.renderer.render(self.count, self.total);
    }

    pub fn update_total(&mut self) {
        self.total += 1;
        self.renderer.render(self.count, self.total);
    }

    pub fn close(&self) {
        self.renderer.terminate(self.count);
    }
}
