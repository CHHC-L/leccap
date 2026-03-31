import Foundation
import CoreGraphics
import ImageIO

guard CommandLine.arguments.count >= 2 else {
    fputs("Usage: swift build_pdf.swift <lecture_dir> [output_pdf]\n", stderr)
    exit(2)
}

let lectureDir = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
let slidesDir = lectureDir.appendingPathComponent("slides", isDirectory: true)
let outputPDF: URL = {
    if CommandLine.arguments.count >= 3 {
        return URL(fileURLWithPath: CommandLine.arguments[2])
    }
    return lectureDir.appendingPathComponent("slides.pdf")
}()

let fileManager = FileManager.default
let slideFiles = try fileManager.contentsOfDirectory(at: slidesDir, includingPropertiesForKeys: nil)
    .filter { $0.pathExtension.lowercased() == "jpg" }
    .sorted { $0.lastPathComponent < $1.lastPathComponent }

guard !slideFiles.isEmpty else {
    fputs("No slide JPGs found in \(slidesDir.path)\n", stderr)
    exit(1)
}

guard let firstSource = CGImageSourceCreateWithURL(slideFiles[0] as CFURL, nil),
      let firstImage = CGImageSourceCreateImageAtIndex(firstSource, 0, nil) else {
    fputs("Failed to open first slide image\n", stderr)
    exit(1)
}

var mediaBox = CGRect(x: 0, y: 0, width: CGFloat(firstImage.width), height: CGFloat(firstImage.height))
guard let consumer = CGDataConsumer(url: outputPDF as CFURL),
      let context = CGContext(consumer: consumer, mediaBox: &mediaBox, nil) else {
    fputs("Failed to create PDF context for \(outputPDF.path)\n", stderr)
    exit(1)
}

for file in slideFiles {
    guard let source = CGImageSourceCreateWithURL(file as CFURL, nil),
          let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
        fputs("Skipping unreadable image: \(file.lastPathComponent)\n", stderr)
        continue
    }
    context.beginPDFPage(nil)
    context.draw(image, in: CGRect(x: 0, y: 0, width: CGFloat(image.width), height: CGFloat(image.height)))
    context.endPDFPage()
}

context.closePDF()
print(outputPDF.path)
