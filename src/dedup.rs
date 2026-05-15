use crate::progress::CLIRenderer;
use crate::progress::ProgressBar;
use crossbeam_channel;
use std::collections::HashSet;
use std::sync::Arc;
use std::sync::Mutex;
use std::{collections::HashMap, io::Read, path::PathBuf, thread};
use walkdir::DirEntry;
use walkdir::WalkDir;
use xxhash_rust::xxh3::Xxh3;

type Job = (DirEntry, Option<u64>);

struct DupHashMap {
    counts: HashMap<u64, Vec<std::path::PathBuf>>,
    dups: HashSet<u64>,
}

impl DupHashMap {
    pub fn new() -> Self {
        Self {
            counts: HashMap::new(),
            dups: HashSet::new(),
        }
    }

    pub fn insert(&mut self, hash: u64, path: &std::path::Path) {
        let v = self.counts.entry(hash).or_insert_with(Vec::new);

        if !v.is_empty() {
            self.dups.insert(hash);
        }

        v.push(path.into());
    }
}

struct Hasher {
    hasher: Xxh3,
}

impl Hasher {
    pub fn new() -> Self {
        Self {
            hasher: Xxh3::with_seed(0),
        }
    }

    pub fn hash_file(&mut self, path: &std::path::Path) -> crate::Result<u64> {
        self.hasher.reset();

        let mut file = std::fs::File::open(path)?;

        let mut buffer = [0; 65536]; // 64KB chunks
        loop {
            match file.read(&mut buffer) {
                Ok(0) => break,
                Ok(n) => self.hasher.update(&buffer[..n]),
                Err(e) => return Err(crate::Error::HashError(e.to_string())),
            }
        }

        let digest = self.hasher.digest();
        Ok(digest)
    }
}

pub fn deduplicate(dir_1: &PathBuf, dir_2: &PathBuf, n_threads: u8) -> crate::Result<()> {
    let progress = Arc::new(Mutex::new(ProgressBar::new(Box::new(CLIRenderer::new(10)))));

    let (tx, rx) = crossbeam_channel::unbounded::<Job>();
    let (tx2, rx2) = crossbeam_channel::unbounded::<Job>();
    let mut handles = vec![];

    for _ in 0..n_threads {
        let (thread_rx, thread_tx) = (rx.clone(), tx2.clone());

        let handle = thread::spawn(move || {
            let mut hasher = Hasher::new();

            for (entry, _) in thread_rx.iter() {
                match hasher.hash_file(entry.path()) {
                    Ok(hash) => {
                        thread_tx
                            .send((entry, Some(hash)))
                            .expect("Failed to send hash for entry {entry}");
                    }
                    Err(e) => println!("{e:?}"),
                }
            }
        });

        handles.push(handle);
    }

    let thread_rx = rx2.clone();
    let thread_progress = progress.clone();
    let files_thread_handle = thread::spawn(move || {
        let mut files = DupHashMap::new();

        for (entry, hash) in thread_rx.iter() {
            files.insert(hash.unwrap(), entry.path());
            thread_progress.lock().unwrap().update_count();
        }

        files
    });

    for entry in WalkDir::new(dir_1).follow_links(true) {
        match entry {
            Ok(ent) => {
                if ent.file_type().is_file() {
                    tx.send((ent, None))
                        .expect("Failed to send job for entry {entry}");
                    progress.lock().unwrap().update_total();
                }
            }
            Err(e) => println!("{e}"),
        }
    }
    for entry in WalkDir::new(dir_2).follow_links(true) {
        match entry {
            Ok(ent) => {
                if ent.file_type().is_file() {
                    tx.send((ent, None))
                        .expect("Failed to send job for entry {entry}");
                    progress.lock().unwrap().update_total();
                }
            }
            Err(e) => println!("{e}"),
        }
    }

    drop(tx);
    drop(tx2);

    for handle in handles {
        handle.join().expect("Failed to join worker thread");
    }
    let _files = files_thread_handle
        .join()
        .expect("Failed to get file hashes");

    let progress = progress.lock().unwrap();
    progress.close();

    if progress.has_completed() {
        Ok(())
    } else {
        Err(crate::Error::ThreadError(
            "Not all tasks were completed".to_owned(),
        ))
    }
}
